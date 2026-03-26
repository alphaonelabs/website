"""
Assignment deadline reminder system for Alpha One Labs.

Handles automatic sending of reminder emails to students when assignments
are due soon. Uses Django signals to automatically create and manage reminders.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from .models import CourseMaterial, Enrollment

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Manages scheduling and sending of assignment deadline reminders."""

    @staticmethod
    def should_send_early_reminder(course_material):
        """
        Check if early reminder (24 hours before) should be sent.
        
        Returns True if:
        - Material has a due_date
        - Reminder hasn't been sent yet
        - Deadline is within 24-48 hours from now
        """
        if not course_material.due_date or course_material.reminder_sent:
            return False

        now = timezone.now()
        time_until_due = course_material.due_date - now
        
        
        return timedelta(hours=24) <= time_until_due <= timedelta(hours=48)

    @staticmethod
    def should_send_final_reminder(course_material):
        """
        Check if final reminder (on deadline day) should be sent.
        
        Returns True if:
        - Material has a due_date
        - Final reminder hasn't been sent yet
        - Deadline is within next 24 hours
        """
        if not course_material.due_date or course_material.final_reminder_sent:
            return False

        now = timezone.now()
        time_until_due = course_material.due_date - now
        
        # Send final reminder if deadline is within 24 hours
        return timedelta(0) <= time_until_due <= timedelta(hours=24)

    @staticmethod
    def send_early_reminder(course_material):
        """Send 24-hour before deadline reminder to all enrolled students."""
        try:
            course = course_material.course
            enrollments = Enrollment.objects.filter(
                course=course,
                status="approved"
            ).select_related("student", "student__profile")

            for enrollment in enrollments:
                student = enrollment.student
                context = {
                    "student_name": student.first_name or student.username,
                    "assignment_title": course_material.title,
                    "course_title": course.title,
                    "due_date": course_material.due_date,
                    "description": course_material.description,
                    "hours_remaining": 24,
                }

                subject = f"Reminder: '{course_material.title}' is due in 24 hours"
                html_message = render_to_string(
                    "emails/assignment_reminder_24h.html",
                    context
                )
                
                send_mail(
                    subject=subject,
                    message=strip_tags(html_message),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                logger.info(
                    f"24-hour reminder sent to {student.username} for "
                    f"assignment '{course_material.title}'"
                )

            # Mark reminder as sent
            course_material.reminder_sent = True
            course_material.save(update_fields=["reminder_sent"])
            logger.info(f"Early reminder sent for {course_material.title}")
            
        except Exception as e:
            logger.error(
                f"Error sending early reminder for {course_material.title}: {str(e)}"
            )

    @staticmethod
    def send_final_reminder(course_material):
        """Send final reminder on deadline day to all enrolled students."""
        try:
            course = course_material.course
            enrollments = Enrollment.objects.filter(
                course=course,
                status="approved"
            ).select_related("student", "student__profile")

            for enrollment in enrollments:
                student = enrollment.student
                context = {
                    "student_name": student.first_name or student.username,
                    "assignment_title": course_material.title,
                    "course_title": course.title,
                    "due_date": course_material.due_date,
                    "description": course_material.description,
                    "is_final": True,
                }

                subject = f"FINAL REMINDER: '{course_material.title}' is due today!"
                html_message = render_to_string(
                    "emails/assignment_reminder_final.html",
                    context
                )
                
                send_mail(
                    subject=subject,
                    message=strip_tags(html_message),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[student.email],
                    html_message=html_message,
                    fail_silently=False,
                )

                logger.info(
                    f"Final reminder sent to {student.username} for "
                    f"assignment '{course_material.title}'"
                )

            # Mark final reminder as sent
            course_material.final_reminder_sent = True
            course_material.save(update_fields=["final_reminder_sent"])
            logger.info(f"Final reminder sent for {course_material.title}")
            
        except Exception as e:
            logger.error(
                f"Error sending final reminder for {course_material.title}: {str(e)}"
            )


@receiver(post_save, sender=CourseMaterial)
def check_and_send_assignment_reminders(sender, instance, created, **kwargs):
    """
    Signal handler to check and send assignment reminders when CourseMaterial is saved.
    
    This runs after every save of a CourseMaterial object and:
    1. Sends 24-hour early reminder if deadline is 24-48 hours away
    2. Sends final reminder if deadline is within 24 hours
    """
    # Only process if material is an assignment with a due date
    if instance.material_type != "assignment" or not instance.due_date:
        return

    # Check and send early reminder
    if ReminderScheduler.should_send_early_reminder(instance):
        ReminderScheduler.send_early_reminder(instance)

    # Check and send final reminder
    if ReminderScheduler.should_send_final_reminder(instance):
        ReminderScheduler.send_final_reminder(instance)


def strip_tags(html):
    """Utility function to strip HTML tags for plain text emails."""
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)
