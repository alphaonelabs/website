from allauth.account.signals import user_signed_up
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from web.encrypted_fields import make_hash

from .models import CourseProgress, Enrollment, LearningStreak, Session, SessionAttendance, UserEncryptedData
from .utils import send_slack_message

User = get_user_model()


@receiver(user_signed_up)
def notify_slack_on_signup(request, user, **kwargs):
    """Send a Slack notification when a new user signs up"""
    is_teacher = getattr(user.profile, "is_teacher", False)
    user_type = "Teacher" if is_teacher else "Student"

    message = (
        f"🎉 New {user_type} Signup!\n" f"*Name:* {user.get_full_name() or user.email}\n" f"*Email:* {user.email}\n"
    )

    send_slack_message(message)


def invalidate_progress_cache(user):
    """Helper function to invalidate a student's progress cache."""
    cache_key = f"user_progress_{user.id}"
    cache.delete(cache_key)


@receiver(post_save, sender=Enrollment)
@receiver(post_delete, sender=Enrollment)
def invalidate_enrollment_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when an enrollment is added or deleted."""
    invalidate_progress_cache(instance.student)


@receiver(post_save, sender=SessionAttendance)
@receiver(post_delete, sender=SessionAttendance)
def invalidate_attendance_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a session attendance record is added or deleted."""
    invalidate_progress_cache(instance.student)


@receiver(post_save, sender=CourseProgress)
@receiver(post_delete, sender=CourseProgress)
def invalidate_course_progress_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a student's course progress is updated or deleted."""
    invalidate_progress_cache(instance.enrollment.student)


@receiver(m2m_changed, sender=CourseProgress.completed_sessions.through)
def invalidate_completed_sessions_cache(sender, instance, action, **kwargs):
    """Invalidate the progress cache when a completed session is added, removed, or cleared."""
    if action in ["post_add", "post_remove", "post_clear"]:
        invalidate_progress_cache(instance.enrollment.student)


@receiver(post_save, sender=LearningStreak)
def invalidate_streak_cache(sender, instance, **kwargs):
    """Invalidate the progress cache when a student's learning streak is updated."""
    invalidate_progress_cache(instance.user)


@receiver(post_save, sender=Session)
@receiver(post_delete, sender=Session)
def invalidate_session_cache(sender, instance, **kwargs):
    """Invalidate the progress cache for all students when a session is added or deleted."""
    enrollments = Enrollment.objects.filter(course=instance.course)
    for enrollment in enrollments:
        invalidate_progress_cache(enrollment.student)


@receiver(post_save, sender=User)
def sync_user_encrypted_data(sender, instance, **kwargs):
    """Keep UserEncryptedData in sync whenever a User's email or username changes."""
    update_fields = kwargs.get("update_fields")
    # If update_fields is specified and neither email nor username is in it, skip.
    if update_fields is not None and not ({"email", "username"} & set(update_fields)):
        return
    UserEncryptedData.objects.update_or_create(
        user=instance,
        defaults={
            "encrypted_email": instance.email,
            "encrypted_username": instance.username,
            "email_hash": make_hash(instance.email.strip()) if instance.email and instance.email.strip() else "",
            "username_hash": (
                make_hash(instance.username.strip()) if instance.username and instance.username.strip() else ""
            ),
        },
    )
