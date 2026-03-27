import os
import random
import string
import time
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from allauth.account.signals import user_signed_up
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from markdownx.models import MarkdownxField
from PIL import Image

from web.utils import calculate_and_update_user_streak


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("info", "Information"),
        ("success", "Success"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default="info")
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(max_length=500, blank=True)
    expertise = models.CharField(max_length=200, blank=True)
    # Avatar fields
    avatar = models.ImageField(upload_to="avatars", blank=True, default="")
    custom_avatar = models.OneToOneField(
        "Avatar", on_delete=models.SET_NULL, null=True, blank=True, related_name="profile"
    )
    is_teacher = models.BooleanField(default=False)
    is_social_media_manager = models.BooleanField(default=False)
    discord_username = models.CharField(max_length=50, blank=True, help_text="Your Discord username (e.g., User#1234)")
    slack_username = models.CharField(max_length=50, blank=True, help_text="Your Slack username")
    github_username = models.CharField(max_length=50, blank=True, help_text="Your GitHub username (without @)")
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    referral_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stripe_account_id = models.CharField(max_length=100, blank=True)
    stripe_account_status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        blank=True,
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Commission rate in percentage (e.g., 10.00 for 10%)",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_profile_public = models.BooleanField(
        default=False, help_text="Toggle to make your profile public so your details and stats are visible."
    )
    how_did_you_hear_about_us = models.TextField(
        blank=True, help_text="How did you hear about us? You can enter text or a link."
    )

    def __str__(self):
        visibility = "Public" if self.is_profile_public else "Private"
        return f"{self.user.username}'s profile ({visibility})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        # Skip image processing for SVG files
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        """Generate a unique referral code."""
        max_attempts = 10
        attempt = 0

        while attempt < max_attempts:
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Profile.objects.filter(referral_code=code).exists():
                return code
            attempt += 1

        # If we've exhausted our attempts, generate a truly unique code using timestamp
        timestamp = int(time.time())
        code = f"{timestamp:x}".upper()[:8]
        return code

    @property
    def total_referrals(self):
        """Return the total number of successful referrals."""
        return self.referrals.count()

    def add_referral_earnings(self, amount):
        """Add referral earnings to the user's balance."""
        self.referral_earnings = self.referral_earnings + amount
        self.save()

    @property
    def can_receive_payments(self):
        return self.is_teacher and self.stripe_account_id and self.stripe_account_status == "verified"


class Avatar(models.Model):
    style = models.CharField(max_length=50, default="circle")
    background_color = models.CharField(max_length=7, default="#FFFFFF")
    top = models.CharField(max_length=50, default="short_flat")
    eyebrows = models.CharField(max_length=50, default="default")
    eyes = models.CharField(max_length=50, default="default")
    nose = models.CharField(max_length=50, default="default")
    mouth = models.CharField(max_length=50, default="default")
    facial_hair = models.CharField(max_length=50, default="none")
    skin_color = models.CharField(max_length=50, default="light")
    hair_color = models.CharField(max_length=7, default="#000000")
    accessory = models.CharField(max_length=50, default="none")
    clothing = models.CharField(max_length=50, default="hoodie")
    clothing_color = models.CharField(max_length=7, default="#0000FF")
    svg = models.TextField(blank=True, help_text="Stored SVG string of the custom avatar")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Avatar for {self.profile.user.username if hasattr(self, 'profile') and self.profile else 'No Profile'}"

    def save(self, *args, **kwargs):
        from python_avatars import (
            AccessoryType,
        )
        from python_avatars import Avatar as PythonAvatar
        from python_avatars import (
            AvatarStyle,
            ClothingType,
            EyebrowType,
            EyeType,
            FacialHairType,
            HairType,
            MouthType,
            NoseType,
            SkinColor,
        )

        # Create avatar using python_avatars
        avatar = PythonAvatar(
            style=getattr(AvatarStyle, self.style.upper(), AvatarStyle.CIRCLE),
            background_color=self.background_color,
            top=getattr(HairType, self.top.upper(), HairType.SHORT_FLAT),
            eyebrows=getattr(EyebrowType, self.eyebrows.upper(), EyebrowType.DEFAULT),
            eyes=getattr(EyeType, self.eyes.upper(), EyeType.DEFAULT),
            nose=getattr(NoseType, self.nose.upper(), NoseType.DEFAULT),
            mouth=getattr(MouthType, self.mouth.upper(), MouthType.DEFAULT),
            facial_hair=getattr(FacialHairType, self.facial_hair.upper(), FacialHairType.NONE),
            skin_color=getattr(SkinColor, self.skin_color.upper(), SkinColor.LIGHT),
            hair_color=self.hair_color,
            accessory=getattr(AccessoryType, self.accessory.upper(), AccessoryType.NONE),
            clothing=getattr(ClothingType, self.clothing.upper(), ClothingType.HOODIE),
            clothing_color=self.clothing_color,
        )

        # Save SVG string
        self.svg = avatar.render()
        super().save(*args, **kwargs)


class Subject(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class", blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class WebRequest(models.Model):
    ip_address = models.CharField(max_length=100, blank=True, default="")
    user = models.CharField(max_length=150, blank=True, default="")
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    agent = models.TextField(blank=True, default="")
    count = models.BigIntegerField(default=1)
    path = models.CharField(max_length=255, blank=True, default="")
    referer = models.CharField(max_length=255, blank=True, default="")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="web_requests", null=True, blank=True)

    def __str__(self):
        return f"{self.path} - {self.count} views"


class Course(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    image = models.ImageField(
        upload_to="course_images", help_text="Course image (will be resized to 300x300 pixels)", blank=True
    )
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses_teaching")
    description = MarkdownxField()
    learning_objectives = MarkdownxField()
    prerequisites = MarkdownxField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    allow_individual_sessions = models.BooleanField(
        default=False, help_text="Allow students to register for individual sessions"
    )
    invite_only = models.BooleanField(
        default=False, help_text="If enabled, students can only enroll with an invitation"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    max_students = models.IntegerField(validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    level = models.CharField(
        max_length=20,
        choices=[
            ("beginner", "Beginner"),
            ("intermediate", "Intermediate"),
            ("advanced", "Advanced"),
        ],
        default="beginner",
    )
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    is_featured = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # Handle image resizing
        if self.image:
            img = Image.open(self.image)
            # Convert to RGB if necessary
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Crop image to a square format
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            img = img.crop((left, top, right, bottom))
            # Resize the image to 300x300 pixels
            img = img.resize((500, 500), Image.Resampling.LANCZOS)
            # Save the resized image
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)
            # Update the ImageField
            file_name = self.image.name
            self.image.delete(save=False)  # Delete old image
            self.image.save(file_name, ContentFile(buffer.getvalue()), save=False)

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def available_spots(self):
        return self.max_students - self.enrollments.count()

    @property
    def average_rating(self):
        avg = float(self.reviews.aggregate(avg=Avg("rating"))["avg"] or 0)
        return round(avg, 2)


class Session(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(max_length=200)
    description = models.TextField()
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_virtual = models.BooleanField(default=True)
    meeting_link = models.URLField(blank=True)
    meeting_id = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Price for individual session registration"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Rollover fields
    enable_rollover = models.BooleanField(
        default=False, help_text="Enable automatic date rollover if no students are enrolled"
    )
    rollover_pattern = models.CharField(
        max_length=20,
        choices=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="weekly",
        blank=True,
        help_text="How often to roll over the session dates",
    )
    original_start_time = models.DateTimeField(
        null=True, blank=True, help_text="Original start time before any rollovers"
    )
    original_end_time = models.DateTimeField(null=True, blank=True, help_text="Original end time before any rollovers")
    is_rolled_over = models.BooleanField(default=False, help_text="Whether this session has been rolled over")
    teacher_confirmed = models.BooleanField(
        default=False, help_text="Whether the teacher has confirmed the rolled over dates"
    )
    latitude = models.DecimalField(
        blank=True,
        decimal_places=6,
        help_text="Latitude coordinate for mapping",
        max_digits=9,
        null=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        blank=True,
        decimal_places=6,
        help_text="Longitude coordinate for mapping",
        max_digits=9,
        null=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    teaching_style = models.CharField(
        max_length=20,
        choices=[
            ("lecture", "Lecture Based"),
            ("student-centered", "Student Centered"),
            ("hybrid", "Hybrid Learning"),
            ("practical", "Practical Learning"),
        ],
        default="hybrid",
        blank=True,
        help_text="What is the teachng style of session",
    )

    class Meta:
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def save(self, *args, **kwargs):
        # Store original times when first created
        # calculate the lat and longitiude dynamically

        if self.location and (self.latitude is None or self.longitude is None):
            self.fetch_coordinates()

        if not self.pk and not self.original_start_time and not self.original_end_time:
            self.original_start_time = self.start_time
            self.original_end_time = self.end_time

        # Handle virtual meeting creation/updates
        is_new = self._state.adding
        old_instance = None if is_new else Session.objects.get(pk=self.pk)

        # First save to get the ID
        super().save(*args, **kwargs)

        if self.is_virtual:
            from .calendar_sync import create_calendar_event, update_calendar_event

            if is_new:
                event_id = create_calendar_event(self)
                if event_id:
                    self.meeting_id = event_id
                    # Update without triggering save() again
                    Session.objects.filter(pk=self.pk).update(meeting_id=event_id)
            elif old_instance and (
                old_instance.start_time != self.start_time
                or old_instance.end_time != self.end_time
                or old_instance.title != self.title
            ):
                update_calendar_event(self)

    def roll_forward(self):
        """Roll the session forward based on the rollover pattern."""
        if not self.enable_rollover or self.teacher_confirmed:
            return False

        now = timezone.now()
        if self.start_time > now:
            return False  # Don't roll forward future sessions

        # Calculate new dates based on pattern
        if self.rollover_pattern == "daily":
            days_to_add = 1
        elif self.rollover_pattern == "weekly":
            days_to_add = 7
        else:  # monthly
            days_to_add = 30

        # Calculate time difference between start and end
        duration = self.end_time - self.start_time

        # Roll forward until we get a future date
        while self.start_time <= now:
            self.start_time += timezone.timedelta(days=days_to_add)
            self.end_time = self.start_time + duration

        self.is_rolled_over = True
        self.teacher_confirmed = False
        return True

    def delete(self, *args, **kwargs):
        # Delete associated calendar event if exists
        if self.is_virtual and self.meeting_id:
            from .calendar_sync import delete_calendar_event

            delete_calendar_event(self)
        super().delete(*args, **kwargs)

    def fetch_coordinates(self):
        """Fetch latitude and longitude using OpenStreetMap's Nominatim API."""
        from .utils import geocode_address

        if not self.location:
            return
        try:
            coordinates = geocode_address(self.location)
            if coordinates:
                self.latitude, self.longitude = coordinates
                print("location store:", self.latitude, self.longitude)
            else:
                print(
                    f"Skipping session {self.id} due to invalid coordinates:",
                    f"lat={self.latitude}, \n lng={self.longitude}",
                )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error("Error geocoding session %s location '%s': %s", self.id, self.location, str(e))

    def is_live(self):
        """Returns True if the session is live right now."""
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def get_absolute_url(self):
        return reverse("course_detail", kwargs={"slug": self.course.slug})


class CourseMaterial(models.Model):
    MATERIAL_TYPES = [
        ("video", "Video"),
        ("image", "Image"),
        ("document", "Document"),
        ("presentation", "Presentation"),
        ("exercise", "Exercise"),
        ("quiz", "Quiz"),
        ("assignment", "Assignment"),  # Add 'assignment' as a valid choice
        ("other", "Other"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPES)
    file = models.FileField(upload_to="course_materials/", blank=True)
    external_url = models.URLField(blank=True, help_text="URL for external content like YouTube videos")
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials",
    )
    order = models.PositiveIntegerField(default=0)
    is_downloadable = models.BooleanField(default=True)
    requires_enrollment = models.BooleanField(
        default=True, help_text="If True, only enrolled students can access full content"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # New fields for assignment deadlines and reminder tracking
    due_date = models.DateTimeField(null=True, blank=True, help_text="Deadline for assignment submission")
    reminder_sent = models.BooleanField(default=False, help_text="Whether an early reminder has been sent")
    final_reminder_sent = models.BooleanField(default=False, help_text="Whether a final reminder has been sent")

    class Meta:
        ordering = ["order", "created_at"]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    def clean(self):
        if not self.file and not self.external_url:
            raise ValidationError("Either a file or external URL must be provided")
        if self.file and self.external_url:
            raise ValidationError("Cannot have both file and external URL")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return ""

    @property
    def file_size(self):
        if not self.file:
            return 0
        try:
            return self.file.size
        except FileNotFoundError:
            return 0

    @property
    def preview_content(self):
        """Returns limited content for non-enrolled users"""
        if self.material_type == "video":
            return self.title
        elif self.material_type == "image":
            return self.title
        return self.title


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("completed", "Completed"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    enrollment_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    payment_intent_id = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"


class SessionAttendance(models.Model):
    STATUS_CHOICES = [
        ("present", "Present"),
        ("absent", "Absent"),
        ("excused", "Excused"),
        ("late", "Late"),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="attendances")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_attendances")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="absent")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["session", "student"]

    def __str__(self):
        return f"{self.student.username} - {self.session.title} ({self.status})"


class CourseProgress(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="progress")
    completed_sessions = models.ManyToManyField(Session, related_name="completed_by")
    last_accessed = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True)

    @property
    def completion_percentage(self):
        total_sessions = self.enrollment.course.sessions.count()
        if total_sessions == 0:
            return 0
        completed = self.completed_sessions.count()
        return int((completed / total_sessions) * 100)

    @property
    def attendance_rate(self):
        total_past_sessions = self.enrollment.course.sessions.filter(start_time__lt=timezone.now()).count()
        if total_past_sessions == 0:
            return 100
        attended = SessionAttendance.objects.filter(
            student=self.enrollment.student,
            session__course=self.enrollment.course,
            status__in=["present", "late"],
        ).count()
        return int((attended / total_past_sessions) * 100)

    def __str__(self):
        return f"{self.enrollment.student.username}'s progress in {self.enrollment.course.title}"


class EducationalVideo(models.Model):
    """Model for educational videos shared by users."""

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Optional - describe what viewers will learn from this video")
    video_url = models.URLField(help_text="URL for external content like YouTube videos")
    category = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="educational_videos")
    uploader = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="educational_videos",
        null=True,
        blank=True,
        help_text="User who uploaded the video. If null, the submission is considered anonymous.",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Educational Video"
        verbose_name_plural = "Educational Videos"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title

    @property
    def thumbnail_url(self):
        """
        Build the URL for YouTube's high-quality default thumbnail.
        Returns None if this isn't a YouTube video.
        """
        vid = self.youtube_id
        if vid:
            return f"https://img.youtube.com/vi/{vid}/hqdefault.jpg"
        return None

    @property
    def youtube_id(self):
        """
        Extract the YouTube video ID, whether it's a long or short URL.
        Returns None if not a YouTube link.
        """
        parsed = urlparse(self.video_url)
        host = parsed.netloc.lower()

        # youtu.be/<id>
        if host in ("youtu.be", "www.youtu.be"):
            return parsed.path.lstrip("/")

        # youtube.com/watch?v=<id>
        if host in ("youtube.com", "www.youtube.com"):
            try:
                return parse_qs(parsed.query).get("v", [None])[0]
            except Exception:
                return None

        return None


class Achievement(models.Model):
    TYPES = [
        ("attendance", "Perfect Attendance"),
        ("completion", "Course Completion"),
        ("participation", "Active Participation"),
        ("excellence", "Academic Excellence"),
        ("quiz", "High Quiz Score"),
        ("streak", "Daily Learning Streak"),
    ]

    BADGE_ICONS = [
        ("fas fa-trophy", "Trophy"),
        ("fas fa-medal", "Medal"),
        ("fas fa-award", "Award"),
        ("fas fa-star", "Star"),
        ("fas fa-certificate", "Certificate"),
        ("fas fa-graduation-cap", "Graduation Cap"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="achievements")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="achievements", null=True, blank=True)
    achievement_type = models.CharField(max_length=20, choices=TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    awarded_at = models.DateTimeField(auto_now_add=True)
    badge_icon = models.CharField(
        max_length=100, blank=True, help_text="Icon class for the badge (e.g., 'fas fa-trophy')"
    )
    criteria_threshold = models.PositiveIntegerField(
        null=True, blank=True, help_text="Optional threshold required to earn this badge"
    )

    def __str__(self):
        return f"{self.student.username} - {self.title}"


class Review(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews_given")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ["student", "course"]

    def __str__(self):
        return f"{self.student.username}'s review of {self.course.title}"


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name="payments",
        help_text="The enrollment this payment is associated with",
    )
    session = models.ForeignKey(
        Session,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments",
        help_text="Specific session this payment is for, if any",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    stripe_payment_intent_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.session:
            return f"Payment for {self.enrollment} - {self.session.title}"
        return f"Payment for {self.enrollment}"


class ForumCategory(models.Model):
    """Categories for organizing forum discussions."""

    name = models.CharField(max_length=100)
    description = models.TextField()
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, help_text="Font Awesome icon class")
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Forum Categories"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ForumTopic(models.Model):
    """Individual forum topics/threads."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.ForeignKey(ForumCategory, on_delete=models.CASCADE, related_name="topics")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_topics")
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    github_issue_url = models.URLField(blank=True, default="", help_text="Link to related GitHub issue")
    github_milestone_url = models.URLField(blank=True, default="", help_text="Link to related GitHub milestone")
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add these methods to the ForumTopic class
    def upvote_count(self):
        """Return the number of upvotes for this topic."""
        return self.votes.filter(vote_type="up").count()

    def downvote_count(self):
        """Return the number of downvotes for this topic."""
        return self.votes.filter(vote_type="down").count()

    def vote_score(self):
        """Return the total vote score (upvotes - downvotes)."""
        return self.upvote_count() - self.downvote_count()

    def user_vote(self, user):
        """Return the user's vote type for this topic, or None if not voted."""
        if not user.is_authenticated:
            return None
        try:
            vote = self.votes.get(user=user)
            return vote.vote_type
        except ForumVote.DoesNotExist:
            return None

    class Meta:
        ordering = ["-is_pinned", "-created_at"]

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    """Replies to forum topics."""

    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_replies")
    content = models.TextField()
    is_solution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Add the same methods to the ForumReply class
    def upvote_count(self):
        """Return the number of upvotes for this reply."""
        return self.votes.filter(vote_type="up").count()

    def downvote_count(self):
        """Return the number of downvotes for this reply."""
        return self.votes.filter(vote_type="down").count()

    def vote_score(self):
        """Return the total vote score (upvotes - downvotes)."""
        return self.upvote_count() - self.downvote_count()

    def user_vote(self, user):
        """Return the user's vote type for this reply, or None if not voted."""
        if not user.is_authenticated:
            return None
        try:
            vote = self.votes.get(user=user)
            return vote.vote_type
        except ForumVote.DoesNotExist:
            return None

    class Meta:
        verbose_name_plural = "Forum Replies"
        ordering = ["created_at"]

    def __str__(self):
        return f"Reply by {self.author.username} on {self.topic.title}"


class PeerConnection(models.Model):
    """Connections between users for networking."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
        ("blocked", "Blocked"),
    ]

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_connections")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_connections")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["sender", "receiver"]

    def __str__(self):
        return f"{self.sender.username} -> {self.receiver.username} ({self.status})"


class PeerMessage(models.Model):
    """Direct messages between connected."""

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    content = models.TextField()
    encrypted_key = models.TextField(blank=True, default="")  # Using default empty string instead of null
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    starred = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

    def save(self, *args, **kwargs):
        if self.read_at and not self.is_read:
            self.is_read = True
        elif self.is_read and not self.read_at:
            self.read_at = timezone.now()
        super().save(*args, **kwargs)


class StudyGroup(models.Model):
    """Study groups for collaborative learning."""

    name = models.CharField(max_length=200)
    description = models.TextField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="study_groups")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(User, related_name="joined_groups", blank=True)
    max_members = models.IntegerField(default=10)
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def can_add_member(self):
        return self.members.count() < self.max_members

    def add_member(self, user):
        if self.can_add_member():
            self.members.add(user)
            return True
        return False

    def is_full(self):
        return self.members.count() >= self.max_members


class StudyGroupInvite(models.Model):
    """Invitations to join study groups."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    group = models.ForeignKey(StudyGroup, on_delete=models.CASCADE, related_name="invites")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_group_invites")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_group_invites")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    STATUS_CHOICES = [("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        unique_together = ["group", "recipient"]

    def __str__(self):
        return f"Invitation to {self.group.name} for {self.recipient.username}"

    def accept(self):
        """Accept the invitation and add the recipient to the study group."""
        self.status = "accepted"
        self.responded_at = timezone.now()
        self.save()
        member_added = self.group.add_member(self.recipient)
        if not member_added:
            # Group is full, create notification or handle this case
            Notification.objects.create(
                user=self.recipient,
                title="Group Full",
                message=f"Could not join {self.group.name} as it's already full",
                notification_type="warning",
            )

    def decline(self):
        """Decline the invitation."""
        self.status = "declined"
        self.responded_at = timezone.now()
        self.save()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a Profile instance when a new User is created."""
    if created and not hasattr(instance, "profile"):
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save the Profile instance when the User is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()
    else:
        Profile.objects.create(user=instance)


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_posts")
    content = MarkdownxField()
    excerpt = models.TextField(blank=True)
    featured_image = models.ImageField(
        upload_to="blog/images/", blank=True, help_text="Featured image for the blog post"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    tags = models.CharField(
        max_length=200, blank=True, help_text="Comma-separated tags (e.g., 'python, django, web development')"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def reading_time(self):
        """Estimate reading time in minutes."""
        words_per_minute = 200
        word_count = len(self.content.split())
        minutes = word_count / words_per_minute
        return max(1, round(minutes))


class BlogComment(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blog_comments")
    content = models.TextField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"


class SuccessStory(models.Model):
    STATUS_CHOICES = [
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="success_stories")
    content = MarkdownxField()
    excerpt = models.TextField(blank=True)
    featured_image = models.ImageField(
        upload_to="success_stories/images/", blank=True, help_text="Featured image for the success story"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="published")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-published_at", "-created_at"]
        verbose_name = "Success Story"
        verbose_name_plural = "Success Stories"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.status == "published" and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("success_story_detail", kwargs={"slug": self.slug})

    @property
    def reading_time(self):
        """Estimate reading time in minutes."""
        words_per_minute = 200
        word_count = len(self.content.split())
        minutes = word_count / words_per_minute
        return max(1, round(minutes))


@receiver(user_signed_up)
def set_user_type(sender, request, user, **kwargs):
    """Set the user type (teacher/student) when they sign up."""
    is_teacher = request.POST.get("is_teacher") == "on"
    profile = user.profile
    profile.is_teacher = is_teacher
    profile.save()


class Cart(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(user__isnull=False) | models.Q(session_key__gt=""),
                name="cart_user_or_session_key",
            )
        ]

    @property
    def item_count(self):
        return self.items.count()

    @property
    def has_goods(self):
        return self.items.filter(goods__isnull=False).exists()

    @property
    def total(self):
        return sum(item.final_price for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return "Anonymous cart"


class Storefront(models.Model):
    teacher = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="storefront", verbose_name="Teacher Profile"
    )
    name = models.CharField(
        max_length=100, unique=True, help_text="Display name for your store", default="Default Store Name"
    )
    description = models.TextField(blank=True, help_text="Describe your store for customers")
    logo = models.ImageField(upload_to="store_logos/", blank=True, help_text="Recommended size: 200x200px")
    store_slug = models.SlugField(unique=True, blank=True, help_text="Auto-generated URL-friendly identifier")
    is_active = models.BooleanField(default=True, help_text="Enable/disable public visibility of your store")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.store_slug:
            self.store_slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base_slug = slugify(self.name)
        unique_slug = base_slug
        count = 1
        while Storefront.objects.filter(store_slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{count}"
            count += 1
        return unique_slug

    def __str__(self):
        return f"{self.name} (by {self.teacher.username})"


class Goods(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ("physical", "Physical Product"),
        ("digital", "Digital Download"),
    ]

    name = models.CharField(max_length=100, help_text="Product title (e.g., 'Algebra Basics Workbook')")
    description = models.TextField(help_text="Detailed product description")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price in USD")
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, help_text="Discounted price (optional)"
    )
    stock = models.PositiveIntegerField(blank=True, null=True, help_text="Leave blank for digital products")
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPE_CHOICES, default="physical")
    file = models.FileField(upload_to="digital_goods/", blank=True, help_text="Required for digital products")
    category = models.CharField(max_length=100, blank=True, help_text="e.g., 'Books', 'Course Materials'")
    images = models.ManyToManyField("ProductImage", related_name="goods_images", blank=True)
    storefront = models.ForeignKey(Storefront, on_delete=models.CASCADE, related_name="goods")
    is_available = models.BooleanField(default=True, help_text="Show/hide product from store")
    is_reward = models.BooleanField(default=False, help_text="Can be unlocked as achievement reward")
    featured = models.BooleanField(default=False, help_text="Mark this product as featured")  # New field
    points_required = models.PositiveIntegerField(
        blank=True, null=True, help_text="Points needed to unlock this reward"
    )
    sku = models.CharField(
        max_length=50, unique=True, blank=True, null=True, help_text="Inventory tracking ID (auto-generated)"
    )
    slug = models.SlugField(unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def image_url(self):
        """Return the URL of the first product image, or a default image if none exists."""
        # Get images using the related name "goods_images" from ProductImage model
        first_image = self.goods_images.first()
        if first_image and first_image.image:
            return first_image.image.url
        # Return a default placeholder image
        return "/static/images/placeholder.png"

    @property
    def image(self):
        first_image = self.goods_images.first()
        if first_image and first_image.image:
            return first_image.image.url
        # Return a default placeholder image
        return "/static/images/placeholder.png"

    def clean(self):
        # Validate discount logic
        if self.discount_price and self.discount_price >= self.price:
            raise ValidationError("Discount price must be lower than original price.")

        # Validate digital product constraints
        if self.product_type == "digital":
            if self.stock is not None:
                raise ValidationError("Digital products cannot have stock quantities.")
            if not self.file:
                raise ValidationError("Digital products require a file upload.")

        # Validate physical product constraints
        if self.product_type == "physical" and self.stock is None:
            raise ValidationError("Physical products must have a stock quantity.")

        # Validate reward items
        if self.is_reward and (self.points_required is None or self.points_required <= 0):
            raise ValidationError("Reward items must have a positive 'points_required' value.")

    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{slugify(self.name[:20])}-{self.id}"
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Goods.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} (${self.price})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            ("cart", "course"),
            ("cart", "session"),
            ("cart", "goods"),
        ]

    def clean(self):
        if not self.course and not self.session and not self.goods:
            raise ValidationError("Either a course, session, or goods must be selected")
        if (self.course and self.session) or (self.course and self.goods) or (self.session and self.goods):
            raise ValidationError("Cannot select more than one type of item")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def price(self):
        if self.course:
            return self.course.price
        if self.session:
            return self.session.price or 0
        if self.goods:
            return self.goods.price
        return 0

    @property
    def final_price(self):
        if self.goods and self.goods.discount_price:  # Check for discount
            return self.goods.discount_price
        return self.price  # Fallback to original price

    def __str__(self):
        if self.course:
            return f"{self.course.title} in cart for {self.cart}"
        if self.session:
            return f"{self.session.title} in cart for {self.cart}"
        if self.goods:
            return f"{self.goods.name} in cart for {self.cart}"
        return "Unknown item in cart"


# Constants
ENROLLMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
]


class SessionEnrollment(models.Model):
    """Model for tracking enrollments in individual sessions."""

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="session_enrollments")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=20, choices=ENROLLMENT_STATUS_CHOICES, default="pending")
    payment_intent_id = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["student", "session"]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.email} - {self.session.title}"


class EventCalendar(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_calendars")
    created_at = models.DateTimeField(auto_now_add=True)
    month = models.IntegerField()  # 0-11 for Jan-Dec
    year = models.IntegerField()
    share_token = models.CharField(max_length=32, unique=True)  # For sharing the calendar

    def save(self, *args, **kwargs):
        if not self.share_token:
            self.share_token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} - {self.month + 1}/{self.year}"

    @property
    def unique_participants_count(self):
        """Count unique participants by name"""
        return self.time_slots.values("name").distinct().count()


class TimeSlot(models.Model):
    calendar = models.ForeignKey(EventCalendar, on_delete=models.CASCADE, related_name="time_slots")
    name = models.CharField(max_length=100)
    day = models.IntegerField()  # 1-31
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["calendar", "name", "day"]  # One slot per person per day

    def __str__(self):
        return f"{self.name} - Day {self.day} ({self.start_time}-{self.end_time})"


class SearchLog(models.Model):
    query = models.CharField(max_length=255)
    results_count = models.IntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    filters_applied = models.JSONField(default=dict, blank=True)
    search_type = models.CharField(
        max_length=20,
        choices=[("course", "Course Search"), ("material", "Material Search"), ("forum", "Forum Search")],
        default="course",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.query} ({self.results_count} results)"


class Challenge(models.Model):
    # defining two types of models
    CHALLENGE_TYPE_CHOICES = [
        ("weekly", "Weekly Challenge"),
        ("one_time", "One-time Challenge"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=10, choices=CHALLENGE_TYPE_CHOICES, default="weekly")
    week_number = models.PositiveIntegerField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["week_number"],
                condition=models.Q(challenge_type="weekly"),
                name="unique_week_number_for_weekly_challenges",
            )
        ]

    def __str__(self):
        if self.challenge_type == "weekly":
            return f"Week {self.week_number}: {self.title}"
        return f"One-time: {self.title}"

    def clean(self):
        super().clean()
        if self.challenge_type == "weekly" and not self.week_number:
            raise ValidationError({"week_number": "Week number is required for weekly challenges."})


class ChallengeSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE)
    submission_text = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    points_awarded = models.PositiveIntegerField(default=10)

    class Meta:
        unique_together = ["user", "challenge"]

    def __str__(self):
        if self.challenge.challenge_type == "weekly":
            return f"{self.user.username}'s submission for Week {self.challenge.week_number}"
        return f"{self.user.username}'s submission for {self.challenge.title}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        from django.db import transaction

        with transaction.atomic():
            super().save(*args, **kwargs)

            if is_new:
                # Add regular points for completing the challenge
                Points.objects.create(
                    user=self.user,
                    challenge=self.challenge,
                    amount=self.points_awarded,
                    reason=f"Completed challenge: Week {self.challenge.week_number}",
                    point_type="regular",
                )

                # Calculate and update streak with error handling
                try:
                    calculate_and_update_user_streak(self.user, self.challenge)
                except Exception as e:
                    # Log the error but don't prevent submission from being saved
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.error(f"Error calculating streak for user {self.user.id}: {e}")


class Points(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="points")
    challenge = models.ForeignKey(
        "Challenge", on_delete=models.CASCADE, null=True, blank=True, related_name="points_awarded"
    )
    amount = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=255, help_text="Reason for awarding points")
    point_type = models.CharField(
        max_length=20,
        default="regular",
        choices=[("regular", "Regular Points"), ("streak", "Streak Points"), ("bonus", "Bonus Points")],
    )
    awarded_at = models.DateTimeField(auto_now_add=True)
    current_streak = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.amount} points for {self.reason}"

    class Meta:
        verbose_name_plural = "Points"
        indexes = [
            models.Index(fields=["user", "awarded_at"]),
            models.Index(fields=["awarded_at"]),
        ]

    @classmethod
    def add_points(cls, user, amount, reason, point_type="regular", challenge=None):
        """Atomic method to add points to a user"""
        from django.db import transaction

        with transaction.atomic():
            return cls.objects.create(
                user=user, challenge=challenge, amount=amount, reason=reason, point_type=point_type
            )

    @classmethod
    def get_user_points_summary(cls, user, period=None):
        """Get summary of user points by period (daily, weekly, monthly, or all-time)"""
        import datetime

        from django.db.models import Sum
        from django.utils import timezone

        query = cls.objects.filter(user=user)

        if period == "daily":
            today = timezone.now().date()
            query = query.filter(awarded_at__date=today)
        elif period == "weekly":
            today = timezone.now().date()
            start_of_week = today - datetime.timedelta(days=today.weekday())
            query = query.filter(awarded_at__date__gte=start_of_week)
        elif period == "monthly":
            today = timezone.now().date()
            start_of_month = today.replace(day=1)
            query = query.filter(awarded_at__date__gte=start_of_month)

        return query.aggregate(total=Sum("amount"))["total"] or 0


class ProductImage(models.Model):
    goods = models.ForeignKey(Goods, on_delete=models.CASCADE, related_name="goods_images")
    image = models.ImageField(upload_to="goods_images/", help_text="Product display image")
    alt_text = models.CharField(max_length=125, blank=True, help_text="Accessibility description for screen readers")

    def __str__(self):
        return f"Image for {self.goods.name}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending Payment"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    storefront = models.ForeignKey(Storefront, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    shipping_address = models.JSONField(blank=True, null=True, help_text="Structured shipping details")
    tracking_number = models.CharField(max_length=100, blank=True)
    terms_accepted = models.BooleanField(default=False, help_text="User accepted terms during checkout")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None  # Check if it's a new order
        super().save(*args, **kwargs)  # Save first to generate an ID

        if is_new and not self.tracking_number:
            self.tracking_number = self.generate_tracking_number()
            super().save(update_fields=["tracking_number"])

    def generate_tracking_number(self):
        return f"TRACK-{self.pk}-{int(time.time())}-{uuid.uuid4().hex[:6].upper()}"

    def __str__(self):
        return f"Order #{self.id} ({self.user.email})"

    def notify_user(self):
        subject = f"Order #{self.id} Status Update"
        message = f"Your order status is now: {self.get_status_display()}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email], fail_silently=False)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    goods = models.ForeignKey(Goods, on_delete=models.PROTECT, verbose_name="Product")
    quantity = models.PositiveIntegerField(default=1)
    price_at_purchase = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    discounted_price_at_purchase = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, editable=False
    )

    class Meta:
        unique_together = [("order", "goods")]
        verbose_name = "Order Line Item"

    def __str__(self):
        return f"{self.quantity}x {self.goods.name}"


class TeamGoal(models.Model):
    """A goal that team members work together to achieve."""

    title = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_goals")
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    STATUS_CHOICES = [("active", "Active"), ("completed", "Completed"), ("cancelled", "Cancelled")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def __str__(self):
        return self.title

    @property
    def completion_percentage(self):
        """Calculate the percentage of members who have completed the goal."""
        total_members = self.members.count()
        if total_members == 0:
            return 0
        completed_members = self.members.filter(completed=True).count()
        return int((completed_members / total_members) * 100)


class TeamGoalMember(models.Model):
    """Represents a member of a team goal."""

    team_goal = models.ForeignKey(TeamGoal, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    completion_image = models.ImageField(upload_to="proof_images/", blank=True)
    completion_link = models.URLField(max_length=200, blank=True)
    completion_notes = models.TextField(blank=True)
    ROLE_CHOICES = [("leader", "Team Leader"), ("member", "Team Member")]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="member")

    class Meta:
        unique_together = ["team_goal", "user"]

    def __str__(self):
        return f"{self.user.username} - {self.team_goal.title}"

    def mark_completed(self):
        """Mark this member's participation as completed."""
        self.completed = True
        self.completed_at = timezone.now()
        self.save()

        Notification.objects.create(
            user=self.team_goal.creator,
            title="Goal Progress Update",
            message=f"{self.user.get_full_name() or self.user.username} completed'{self.team_goal.title}'",
            notification_type="success",
        )


class TeamInvite(models.Model):
    """Invitation to join a team goal."""

    goal = models.ForeignKey(TeamGoal, on_delete=models.CASCADE, related_name="invites")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invites")
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_invites")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    STATUS_CHOICES = [("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    class Meta:
        unique_together = ["goal", "recipient"]

    def __str__(self):
        return f"Invite to {self.goal.title} for {self.recipient.username}"

    def save(self, *args, **kwargs):
        created = not self.pk
        super().save(*args, **kwargs)

        if created and self.status == "pending":
            Notification.objects.create(
                user=self.recipient,
                title="New Team Invitation",
                message=f"Invited to '{self.goal.title}' by {self.sender.get_full_name() or self.sender.username}",
                notification_type="info",
            )

        # Create notification when invite is accepted
        if not created and self.status == "accepted":
            Notification.objects.create(
                user=self.sender,
                title="Team Invitation Accepted",
                message=f"{self.recipient.get_full_name() or self.recipient.username} has accepted your invitation",
                notification_type="success",
            )


def validate_image_size(image):
    """Validate that the image file is not too large."""
    file_size = image.size
    limit_mb = 2
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Image file is too large. Size should not exceed {limit_mb} MB.")


def validate_image_extension(image):
    """Validate that the file is a valid image type."""
    import os

    ext = os.path.splitext(image.name)[1]
    valid_extensions = [".jpg", ".jpeg", ".png", ".gif"]
    if ext.lower() not in valid_extensions:
        raise ValidationError("Unsupported file type. Please use JPEG, PNG, or GIF images.")


class Meme(models.Model):
    title = models.CharField(max_length=200, blank=False, help_text=_("A descriptive title for the meme"))
    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        related_name="memes",
        null=True,
        blank=False,
        help_text=_("The educational subject this meme relates to"),
    )
    caption = models.TextField(help_text=_("The text content of the meme"), blank=True)
    image = models.ImageField(
        upload_to="memes/",
        validators=[validate_image_size, validate_image_extension],
        help_text=_("Upload a meme image (JPG, PNG, or GIF, max 2MB)"),
    )
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="memes", null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.title)
            # it has to be unique
            original_slug = self.slug
            counter = 1
            while Meme.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"]), models.Index(fields=["subject"])]
        verbose_name = _("Meme")
        verbose_name_plural = _("Memes")


class Donation(models.Model):
    """Model for storing donation information."""

    DONATION_TYPES = (
        ("one_time", "One-time Donation"),
        ("subscription", "Monthly Subscription"),
    )

    DONATION_STATUS = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="donations")
    email = models.EmailField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    donation_type = models.CharField(max_length=20, choices=DONATION_TYPES)
    status = models.CharField(max_length=20, choices=DONATION_STATUS, default="pending")
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True, default="")
    stripe_subscription_id = models.CharField(max_length=100, blank=True, default="")
    stripe_customer_id = models.CharField(max_length=100, blank=True, default="")
    message = models.TextField(blank=True)
    anonymous = models.BooleanField(default=False)
    award_points = models.BooleanField(default=True, help_text="Award points to user for donation")
    points_multiplier = models.DecimalField(
        decimal_places=2, max_digits=5, default=1.0, help_text="Points per dollar multiplier"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email} - {self.amount} ({self.get_donation_type_display()})"

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_recurring(self):
        return self.donation_type == "subscription"

    @property
    def display_name(self):
        if self.anonymous:
            return "Anonymous"
        if self.user:
            return self.user.get_full_name() or self.user.username
        return self.email.split("@")[0]  # Use part before @ in email


class Badge(models.Model):
    BADGE_TYPES = [
        ("challenge", "Challenge Completion"),
        ("course", "Course Completion"),
        ("achievement", "Special Achievement"),
        ("teacher_awarded", "Teacher Awarded"),
    ]
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to="badges/")
    badge_type = models.CharField(max_length=20, choices=BADGE_TYPES)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True, related_name="badges")
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, null=True, blank=True, related_name="badges")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_badges")
    is_active = models.BooleanField(default=True)
    criteria = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            buffer = BytesIO()
            img.save(buffer, format="PNG", quality=90)
            file_name = self.image.name
            self.image.delete(save=False)
            self.image.save(file_name, ContentFile(buffer.getvalue()), save=False)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["badge_type", "name"]


class UserBadge(models.Model):
    AWARD_METHODS = [
        ("challenge_completion", "Challenge Completion"),
        ("course_completion", "Course Completion"),
        ("teacher_awarded", "Teacher Awarded"),
        ("system_awarded", "System Awarded"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="awarded_to")
    award_method = models.CharField(max_length=20, choices=AWARD_METHODS)
    awarded_at = models.DateTimeField(auto_now_add=True)
    challenge_submission = models.ForeignKey(
        ChallengeSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name="badges"
    )
    course_enrollment = models.ForeignKey(
        Enrollment, on_delete=models.SET_NULL, null=True, blank=True, related_name="badges"
    )
    awarded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="awarded_badges"
    )
    award_message = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"

    class Meta:
        unique_together = ["user", "badge"]
        ordering = ["-awarded_at"]


@receiver(post_save, sender=ChallengeSubmission)
def award_challenge_badge(sender, instance, created, **kwargs):
    if created:
        challenge_badges = Badge.objects.filter(challenge=instance.challenge, badge_type="challenge", is_active=True)
        for badge in challenge_badges:
            if not UserBadge.objects.filter(user=instance.user, badge=badge).exists():
                UserBadge.objects.create(
                    user=instance.user, badge=badge, award_method="challenge_completion", challenge_submission=instance
                )
                Notification.objects.create(
                    user=instance.user,
                    title=f"New Badge: {badge.name}",
                    message=f"Congrats! You've earned {badge.name} for completing {instance.challenge.title}",
                    notification_type="success",
                )


@receiver(post_save, sender=Enrollment)
def award_course_completion_badge(sender, instance, **kwargs):
    if instance.status == "completed":
        course_badges = Badge.objects.filter(course=instance.course, badge_type="course", is_active=True)
        for badge in course_badges:
            if not UserBadge.objects.filter(user=instance.student, badge=badge).exists():
                UserBadge.objects.create(
                    user=instance.student, badge=badge, award_method="course_completion", course_enrollment=instance
                )
                Notification.objects.create(
                    user=instance.student,
                    title=f"New Badge: {badge.name}",
                    message=f"Congrats! You've earned {badge.name} for completing {instance.course.title}",
                    notification_type="success",
                )


def award_badge_to_student(badge_id, student_id, teacher_id, message=""):
    try:
        badge = Badge.objects.get(id=badge_id)
        student = User.objects.get(id=student_id)
        teacher = User.objects.get(id=teacher_id)
        if not teacher.profile.is_teacher:
            return None
        if UserBadge.objects.filter(user=student, badge=badge).exists():
            return None
        user_badge = UserBadge.objects.create(
            user=student, badge=badge, award_method="teacher_awarded", awarded_by=teacher, award_message=message
        )
        Notification.objects.create(
            user=student,
            title=f"New Badge: {badge.name}",
            message=f"You were awarded {badge.name} by {teacher.username}. {message}",
            notification_type="success",
        )
        return user_badge
    except (Badge.DoesNotExist, User.DoesNotExist):
        return None


def get_user_badges(self):
    return UserBadge.objects.filter(user=self.user)


Profile.get_user_badges = get_user_badges


class Certificate(models.Model):
    # Certificate Model
    certificate_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    completion_date = models.DateField(auto_now_add=True)
    course = models.ForeignKey(
        "web.Course", on_delete=models.CASCADE, related_name="certificates", null=True, blank=True
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")

    # New fields added as per feedback
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        course_title = self.course.title if self.course else "No Course"
        return f"Certificate for {self.user.username} - {course_title}"

    def clean(self):
        """Validate that the user has completed the course."""
        from django.core.exceptions import ValidationError

        if self.course and self.user:
            # Check if the user is enrolled in the course
            enrollment = Enrollment.objects.filter(student=self.user, course=self.course, status="completed").exists()

            if not enrollment:
                raise ValidationError("User has not completed this course.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class ProgressTracker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress_trackers")
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    current_value = models.IntegerField(default=0)
    target_value = models.IntegerField()
    color = models.CharField(
        max_length=20,
        default="blue-600",
        choices=[
            ("blue-600", "Primary"),
            ("green-600", "Success"),
            ("yellow-600", "Warning"),
            ("red-600", "Danger"),
            ("gray-600", "Secondary"),
        ],
    )
    public = models.BooleanField(default=True)
    embed_code = models.CharField(max_length=36, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.embed_code:
            import uuid

            self.embed_code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    @property
    def percentage(self):
        if self.target_value == 0:
            return 0
        return min(100, int((self.current_value / self.target_value) * 100))

    def __str__(self):
        return f"{self.title} ({self.percentage}%)"


class LearningStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_streak")
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_engagement = models.DateField(null=True, blank=True)

    def update_streak(self):
        today = timezone.now().date()
        # Check if last engagement is in the future
        if self.last_engagement and self.last_engagement > today:
            # Treat future date as invalid and reset the streak
            self.current_streak = 1
        # If first engagement or gap > 1 day, reset streak to 1
        elif not self.last_engagement or (today - self.last_engagement).days > 1:
            self.current_streak = 1
        # If last engagement was yesterday, increment streak
        elif (today - self.last_engagement).days == 1:
            self.current_streak += 1
        # Else (if already engaged today), do nothing to the streak count

        # Update the last engagement to today
        self.last_engagement = today
        # Update longest streak if current is higher
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        self.save()

    def __str__(self):
        return f"{self.user.username} - Current: {self.current_streak}, Longest: {self.longest_streak}"


class Quiz(models.Model):
    """Model for storing custom quizzes created by users."""

    STATUS_CHOICES = [("draft", "Draft"), ("published", "Published"), ("private", "Private")]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_quizzes")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="quizzes")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_code = models.CharField(
        max_length=8, unique=True, blank=True, null=True, help_text="Unique code for sharing the quiz"
    )
    allow_anonymous = models.BooleanField(
        default=False, help_text="If enabled, users don't need to log in to take this quiz"
    )
    show_correct_answers = models.BooleanField(default=False, help_text="Show correct answers after quiz completion")
    randomize_questions = models.BooleanField(default=False, help_text="Randomize the order of questions")
    time_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Time limit in minutes (optional)")
    max_attempts = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of attempts allowed (leave blank for unlimited)"
    )
    passing_score = models.PositiveIntegerField(default=70, help_text="Minimum percentage required to pass the quiz")

    class Meta:
        verbose_name_plural = "Quizzes"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Generate a unique share code if not provided
        if not self.share_code:
            import random
            import string

            while True:
                code = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
                if not Quiz.objects.filter(share_code=code).exists():
                    self.share_code = code
                    break
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("quiz_detail", kwargs={"pk": self.pk})

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def completion_count(self):
        return self.user_quizzes.filter(completed=True).count()


class QuizQuestion(models.Model):
    """Model for storing quiz questions."""

    QUESTION_TYPES = [("multiple", "Multiple Choice"), ("true_false", "True/False"), ("short", "Short Answer")]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES, default="multiple")
    explanation = models.TextField(blank=True, help_text="Explanation of the correct answer")
    points = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="quiz_questions/", blank=True, default="")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.text[:50]}{'...' if len(self.text) > 50 else ''}"


class QuizOption(models.Model):
    """Model for storing answer options for quiz questions."""

    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class UserQuiz(models.Model):
    """Model for tracking user quiz attempts and responses"""

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="user_quizzes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quiz_attempts", null=True, blank=True)
    anonymous_id = models.CharField(
        max_length=36, blank=True, default="", help_text="Identifier for non-logged-in users"
    )
    score = models.PositiveIntegerField(default=0)
    max_score = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict, blank=True, help_text="JSON storing the user's answers and question IDs")

    class Meta:
        ordering = ["-start_time"]
        verbose_name_plural = "User quiz attempts"

    def __str__(self):
        user_str = self.user.username if self.user else f"Anonymous ({self.anonymous_id})"
        return f"{user_str} - {self.quiz.title}"

    def calculate_score(self):
        """Calculate the score based on answers."""
        score = 0
        max_score = 0

        for q_id, answer_data in self.answers.items():
            try:
                question = QuizQuestion.objects.get(id=q_id)
                max_score += question.points

                if question.question_type == "multiple":
                    # Check if selected options match correct options
                    correct_options = set(question.options.filter(is_correct=True).values_list("id", flat=True))
                    selected_options = set(answer_data.get("selected_options", []))
                    if correct_options == selected_options:
                        score += question.points
                elif question.question_type == "true_false":
                    # For true/false, there should be only one correct option
                    correct_option = question.options.filter(is_correct=True).first()
                    if correct_option and str(correct_option.id) == str(answer_data.get("selected_option")):
                        score += question.points
                elif question.question_type == "short":
                    # Short answers require manual grading in this implementation
                    # We could implement auto-grading logic here for simple cases
                    pass
            except QuizQuestion.DoesNotExist:
                pass

        self.score = score
        self.max_score = max_score
        self.save()

    def complete_quiz(self):
        """Mark the quiz as completed and calculate final score."""
        from django.utils import timezone

        self.completed = True
        self.end_time = timezone.now()
        self.calculate_score()
        self.save()

    @property
    def duration(self):
        """Return the duration of the quiz attempt as a formatted string."""
        if self.start_time and self.end_time:
            # Calculate duration in seconds
            duration_seconds = (self.end_time - self.start_time).total_seconds()

            # Format the duration
            if duration_seconds < 60:
                # Show with decimal precision for small durations
                if duration_seconds < 10:
                    return f"{duration_seconds:.1f}s"
                return f"{int(duration_seconds)}s"

            minutes, seconds = divmod(int(duration_seconds), 60)
            if minutes < 60:
                return f"{minutes}m {seconds}s"

            hours, minutes = divmod(minutes, 60)
            return f"{hours}h {minutes}m {seconds}s"
        elif self.start_time and not self.end_time and self.completed:
            # If completed but no end_time, use current time
            from django.utils import timezone

            duration_seconds = (timezone.now() - self.start_time).total_seconds()

            # Format the duration
            if duration_seconds < 60:
                # Show with decimal precision for small durations
                if duration_seconds < 10:
                    return f"{duration_seconds:.1f}s"
                return f"{int(duration_seconds)}s"

            minutes, seconds = divmod(int(duration_seconds), 60)
            if minutes < 60:
                return f"{minutes}m {seconds}s"

            hours, minutes = divmod(minutes, 60)
            return f"{hours}h {minutes}m {seconds}s"
        return "N/A"

    @property
    def status(self):
        """Return the status of the quiz attempt."""
        if not self.completed:
            return "in_progress"

        # Check if there's a passing score defined on the quiz
        passing_score = getattr(self.quiz, "passing_score", 0)
        if passing_score and self.score >= passing_score:
            return "passed"
        else:
            return "failed"

    def get_status_display(self):
        """Return a human-readable status."""
        if self.status == "passed":
            return "Passed"
        elif self.status == "failed":
            return "Failed"
        else:
            return "In Progress"

    @property
    def created_at(self):
        """Alias for start_time for template compatibility."""
        return self.start_time


class WaitingRoom(models.Model):
    """Model for storing waiting room requests.

    Can be used for two purposes:
    1. Waiting for a new course to be created on a subject/topic (creator, title, subject, topics are set)
    2. Waiting for the next session of an existing course (course is set)
    """

    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed"), ("fulfilled", "Fulfilled")]

    # For waiting for new courses
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=100, blank=True)
    topics = models.TextField(help_text="Comma-separated list of topics", blank=True)
    email = models.EmailField(blank=True, help_text="Email for anonymous users")
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="created_waiting_rooms", null=True, blank=True
    )
    fulfilled_course = models.ForeignKey(
        "Course", on_delete=models.SET_NULL, null=True, blank=True, related_name="fulfilled_waiting_rooms"
    )

    # For waiting for next session of existing course
    course = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="session_waiting_rooms",
        help_text="For waiting for next session of an existing course",
    )

    # Common fields
    participants = models.ManyToManyField(User, related_name="joined_waiting_rooms", blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        if self.course:
            return f"Waiting room for next session of {self.course.title}"
        return self.title or "Untitled Waiting Room"

    def participant_count(self):
        """Return the number of participants in the waiting room."""
        return self.participants.count()

    def topic_list(self):
        """Return the list of topics as a list."""
        if not self.topics:
            return []
        return [topic.strip() for topic in self.topics.split(",") if topic.strip()]

    def get_next_session(self):
        """Get the next upcoming session for this course (if waiting for existing course)."""
        if not self.course:
            return None
        from django.utils import timezone

        return self.course.sessions.filter(start_time__gt=timezone.now()).order_by("start_time").first()

    def mark_as_fulfilled(self, course=None):
        """Mark the waiting room as fulfilled and notify participants."""
        self.status = "fulfilled"
        self.save()

        if course:
            from .notifications import notify_waiting_room_fulfilled

            notify_waiting_room_fulfilled(self, course)

    def close_waiting_room(self):
        """Close the waiting room."""
        self.status = "closed"
        self.save()


class GradeableLink(models.Model):
    """Model for storing links that users want to get grades on."""

    LINK_TYPES = [
        ("pr", "Pull Request"),
        ("article", "Article"),
        ("website", "Website"),
        ("project", "Project"),
        ("other", "Other"),
    ]

    title = models.CharField(max_length=200)
    url = models.URLField()
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submitted_links")
    link_type = models.CharField(max_length=20, choices=LINK_TYPES, default="other")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("gradeable_link_detail", kwargs={"pk": self.pk})

    @property
    def average_grade(self):
        """Calculate the average numeric grade."""
        grades = self.grades.all()
        if not grades:
            return None
        return sum(grade.numeric_grade for grade in grades) / grades.count()

    @property
    def average_letter_grade(self):
        """Convert the average numeric grade back to a letter grade."""
        avg = self.average_grade
        if avg is None:
            return "No grades yet"

        if avg >= 4.0:
            return "A+"
        elif avg >= 3.7:
            return "A"
        elif avg >= 3.3:
            return "A-"
        elif avg >= 3.0:
            return "B+"
        elif avg >= 2.7:
            return "B"
        elif avg >= 2.3:
            return "B-"
        elif avg >= 2.0:
            return "C+"
        elif avg >= 1.7:
            return "C"
        elif avg >= 1.3:
            return "C-"
        elif avg >= 1.0:
            return "D"
        else:
            return "F"

    @property
    def grade_count(self):
        """Return the number of grades."""
        return self.grades.count()

    @property
    def grade_distribution(self):
        """Return a dictionary with the distribution of letter grades."""
        grades = self.grades.all()
        distribution = {}

        # Initialize with all possible grades
        for grade_code, grade_name in LinkGrade.GRADE_CHOICES:
            # Group by main letter for simplicity (A+, A, A- all grouped as A)
            main_letter = grade_code[0]
            distribution[main_letter] = distribution.get(main_letter, 0)

        # Count actual grades
        for grade in grades:
            main_letter = grade.grade[0]
            distribution[main_letter] = distribution.get(main_letter, 0) + 1

        # Sort by grade letter (A, B, C, D, F)
        return {k: v for k, v in sorted(distribution.items())}


class LinkGrade(models.Model):
    """Model for storing grades on links."""

    GRADE_CHOICES = [
        ("A+", "A+"),
        ("A", "A"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B", "B"),
        ("B-", "B-"),
        ("C+", "C+"),
        ("C", "C"),
        ("C-", "C-"),
        ("D", "D"),
        ("F", "F"),
    ]

    GRADE_VALUES = {
        "A+": 4.3,
        "A": 4.0,
        "A-": 3.7,
        "B+": 3.3,
        "B": 3.0,
        "B-": 2.7,
        "C+": 2.3,
        "C": 2.0,
        "C-": 1.7,
        "D": 1.0,
        "F": 0.0,
    }

    link = models.ForeignKey(GradeableLink, on_delete=models.CASCADE, related_name="grades")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="given_grades")
    grade = models.CharField(max_length=2, choices=GRADE_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["link", "user"]  # One grade per user per link
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} graded {self.link.title} with {self.grade}"

    @property
    def numeric_grade(self):
        """Convert letter grade to numeric value."""
        return self.GRADE_VALUES.get(self.grade, 0.0)

    def clean(self):
        """Validate that comments are provided for lower grades."""
        if self.grade not in ["A+", "A"] and not self.comment:
            raise ValidationError("A comment is required for grades below A.")


class PeerChallenge(models.Model):
    """Model for challenges between users for quizzes or tasks."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="peer_challenges")
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_challenges")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Peer Challenge"
        verbose_name_plural = "Peer Challenges"

    def __str__(self):
        return f"{self.title} by {self.creator.username}"

    @property
    def is_expired(self):
        """Check if the challenge has expired."""
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def total_participants(self):
        """Get the total number of participants in this challenge."""
        return self.invitations.filter(status__in=["accepted", "completed"]).count() + 1  # +1 for creator

    @property
    def leaderboard(self):
        """Get sorted list of participants by score."""
        participants = []

        # Add creator's best attempt
        creator_attempts = (
            UserQuiz.objects.filter(quiz=self.quiz, user=self.creator, completed=True, start_time__gte=self.created_at)
            .order_by("-score")
            .first()
        )

        if creator_attempts:
            participants.append(
                {
                    "user": self.creator,
                    "score": creator_attempts.score,
                    "max_score": creator_attempts.max_score,
                    "completion_time": creator_attempts.end_time,
                    "is_creator": True,
                }
            )

        # Add invited participants' best attempts
        for invitation in self.invitations.filter(status="completed"):
            participant_attempt = invitation.user_quiz
            if participant_attempt and participant_attempt.completed:
                participants.append(
                    {
                        "user": invitation.participant,
                        "score": participant_attempt.score,
                        "max_score": participant_attempt.max_score,
                        "completion_time": participant_attempt.end_time,
                        "is_creator": False,
                    }
                )

        # Sort by score (descending) and completion time (ascending)
        return sorted(participants, key=lambda x: (-x["score"], x["completion_time"]))


class PeerChallengeInvitation(models.Model):
    """Model for invitations to peer challenges."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("completed", "Completed"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]

    challenge = models.ForeignKey(PeerChallenge, on_delete=models.CASCADE, related_name="invitations")
    participant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="challenge_invitations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    user_quiz = models.ForeignKey(
        UserQuiz, on_delete=models.SET_NULL, null=True, blank=True, related_name="challenge_invitation"
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["challenge", "participant"]

    def __str__(self):
        return f"{self.challenge.title} invitation for {self.participant.username}"

    def accept(self):
        """Accept the challenge invitation."""
        self.status = "accepted"
        self.save()

        # Create notification for challenge creator
        Notification.objects.create(
            user=self.challenge.creator,
            title="Challenge Accepted",
            message=f"{self.participant.username} has accepted your challenge: {self.challenge.title}",
            notification_type="info",
        )

    def decline(self):
        """Decline the challenge invitation."""
        self.status = "declined"
        self.save()

        # Create notification for challenge creator
        Notification.objects.create(
            user=self.challenge.creator,
            title="Challenge Declined",
            message=f"{self.participant.username} has declined your challenge: {self.challenge.title}",
            notification_type="info",
        )

    def complete(self, user_quiz):
        """Mark the challenge as completed."""
        self.status = "completed"
        self.user_quiz = user_quiz
        self.save()

        # Create notification for challenge creator
        Notification.objects.create(
            user=self.challenge.creator,
            title="Challenge Completed",
            message=f"{self.participant.username} has completed your challenge: {self.challenge.title}",
            notification_type="success",
        )


class NoteHistory(models.Model):
    """Model for tracking changes to teacher notes on enrollments."""

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="note_history")
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="note_history_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_by.username} updated notes for {self.enrollment.student.username}"


class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
    reminder_days_before = models.IntegerField(default=3, help_text="Days before deadline to send first reminder")
    reminder_hours_before = models.IntegerField(default=24, help_text="Hours before deadline to send final reminder")
    email_notifications = models.BooleanField(default=True)
    in_app_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preferences for {self.user.username}"


class FeatureVote(models.Model):
    VOTE_CHOICES = (
        ("up", "Thumbs Up"),
        ("down", "Thumbs Down"),
    )

    feature_id = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    vote = models.CharField(max_length=4, choices=VOTE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["feature_id", "user"], name="web_feature_feature_9fbd0b_idx"),
            models.Index(fields=["feature_id", "ip_address"], name="web_feature_feature_988c48_idx"),
        ]
        verbose_name = "Feature Vote"
        verbose_name_plural = "Feature Votes"
        constraints = [
            models.UniqueConstraint(
                fields=["feature_id", "user"],
                name="unique_user_feature_vote",
                condition=models.Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["feature_id", "ip_address"],
                name="unique_ip_feature_vote",
                condition=models.Q(ip_address__isnull=False),
            ),
        ]

    def clean(self):
        """Validate that a user or IP address hasn't already voted on this feature."""
        if not self.feature_id:
            raise ValidationError({"feature_id": "Feature ID is required"})

        if not self.vote:
            raise ValidationError({"vote": "Vote is required"})

        if not self.user and not self.ip_address:
            raise ValidationError("Either user or IP address must be provided")

        if self.user and self.ip_address:
            raise ValidationError("Cannot provide both user and IP address")

        if self.user:
            # Check for existing user vote
            existing_vote = (
                FeatureVote.objects.filter(feature_id=self.feature_id, user=self.user).exclude(pk=self.pk).first()
            )
            if existing_vote:
                raise ValidationError(
                    {"user": f"User has already voted on this feature with a {existing_vote.get_vote_display()}"}
                )
        elif self.ip_address:
            # Check for existing IP vote
            existing_vote = (
                FeatureVote.objects.filter(feature_id=self.feature_id, ip_address=self.ip_address, user__isnull=True)
                .exclude(pk=self.pk)
                .first()
            )
            if existing_vote:
                raise ValidationError(
                    {
                        "ip_address": (
                            f"IP address has already voted on this feature with a "
                            f"{existing_vote.get_vote_display()}"
                        )
                    }
                )

    def save(self, *args, **kwargs):
        """Ensure clean() is called before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        voter = self.user.username if self.user else self.ip_address
        return f"{self.get_vote_display()} for {self.feature_id} by {voter}"


class MembershipPlan(models.Model):
    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    features = models.JSONField(default=list)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2)
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default="monthly")
    stripe_monthly_price_id = models.CharField(max_length=100, blank=True)
    stripe_yearly_price_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def yearly_savings(self):
        if self.price_monthly and self.price_yearly:
            monthly_total = self.price_monthly * 12
            savings = monthly_total - self.price_yearly
            if savings > 0:
                return int((savings / monthly_total) * 100)
        return 0

    def __str__(self):
        return f"{self.name} - ${self.price_monthly}/month or ${self.price_yearly}/year"


class UserMembership(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("canceled", "Canceled"),
        ("trialing", "Trialing"),
        ("unpaid", "Unpaid"),
        ("incomplete", "Incomplete"),
        ("expired", "Expired"),
    ]

    BILLING_PERIOD_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    user = models.OneToOneField("auth.User", on_delete=models.CASCADE, related_name="membership")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="user_memberships")
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default="monthly")
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        active_statuses = ["active", "trialing"]
        return self.status in active_statuses and (self.end_date is None or self.end_date > timezone.now())

    @property
    def is_canceled(self):
        return self.status == "canceled" or self.cancel_at_period_end

    @property
    def days_until_expiration(self):
        if not self.end_date:
            return None
        now = timezone.now()
        if now > self.end_date:
            return -1
        return (self.end_date - now).days

    def get_next_billing_date(self):
        if self.end_date:
            return self.end_date
        return None

    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"


class MembershipSubscriptionEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("canceled", "Canceled"),
        ("payment_succeeded", "Payment Succeeded"),
        ("payment_failed", "Payment Failed"),
        ("reactivated", "Reactivated"),
    ]

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="membership_events")
    membership = models.ForeignKey(UserMembership, on_delete=models.SET_NULL, null=True, related_name="events")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES)
    stripe_event_id = models.CharField(max_length=100, blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} - {self.user.email} - {self.created_at}"


class ScheduledPost(models.Model):
    content = models.CharField(max_length=280)
    image = models.ImageField(upload_to="scheduled_posts/", blank=True)
    scheduled_time = models.DateTimeField()
    posted = models.BooleanField(default=False)
    posted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.content


class ForumVote(models.Model):
    """Model for storing votes on forum topics and replies."""

    VOTE_TYPES = [
        ("up", "Upvote"),
        ("down", "Downvote"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_votes")
    topic = models.ForeignKey("ForumTopic", on_delete=models.CASCADE, related_name="votes", null=True, blank=True)
    reply = models.ForeignKey("ForumReply", on_delete=models.CASCADE, related_name="votes", null=True, blank=True)
    vote_type = models.CharField(max_length=4, choices=VOTE_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "topic"), ("user", "reply")]
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(topic__isnull=False, reply__isnull=True)
                    | models.Q(topic__isnull=True, reply__isnull=False)
                ),
                name="vote_topic_xor_reply",
            )
        ]

    def __str__(self):
        if self.topic:
            return f"{self.user.username} {self.vote_type}voted topic #{self.topic.id}"
        elif self.reply:
            return f"{self.user.username} {self.vote_type}voted reply #{self.reply.id}"
        return f"{self.user.username} cast a vote"


def default_valid_until() -> datetime:
    return timezone.now() + timedelta(days=30)


class Discount(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(default=default_valid_until)
    used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code} for {self.user.username} on {self.course.title}"


class VideoRequest(models.Model):
    """Model for users to request educational videos on specific topics."""

    title = models.CharField(max_length=200, help_text="Short title describing the requested video")
    description = models.TextField(help_text="Detailed description of what you'd like to learn from this video")
    category = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="video_requests")
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name="video_requests")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("fulfilled", "Fulfilled"),
            ("rejected", "Rejected"),
        ],
        default="pending",
    )
    fulfilled_by = models.ForeignKey(
        EducationalVideo,
        on_delete=models.SET_NULL,
        related_name="fulfilling_requests",
        null=True,
        blank=True,
        help_text="Educational video that fulfills this request",
    )

    class Meta:
        verbose_name = "Video Request"
        verbose_name_plural = "Video Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class Survey(models.Model):
    title = models.CharField(max_length=200)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)  # Added null=True
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Question(models.Model):
    QUESTION_TYPES = [
        ("mcq", "Multiple Choice"),
        ("checkbox", "Checkbox (Multiple Answers)"),
        ("text", "Text Answer"),
        ("true_false", "True/False"),
        ("scale", "Scale Rating"),
    ]

    survey = models.ForeignKey("Survey", on_delete=models.CASCADE)
    text = models.TextField()
    type = models.CharField(max_length=20, choices=QUESTION_TYPES, default="mcq")
    required = models.BooleanField(default=True)
    scale_min = models.IntegerField(default=1)
    scale_max = models.IntegerField(default=5)

    def __str__(self):
        return self.text


class Choice(models.Model):
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    text = models.CharField(max_length=200)

    def __str__(self):
        return self.text


class Response(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey("Question", on_delete=models.CASCADE)
    choice = models.ForeignKey("Choice", on_delete=models.CASCADE, blank=True, null=True)
    text_answer = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response by {self.user.username} to {self.question.text}"


class VirtualClassroom(models.Model):
    """Model for storing virtual classroom instances."""

    name = models.CharField(max_length=200)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="virtual_classrooms")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="virtual_classrooms", null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    max_students = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} - {self.teacher.username}"


class VirtualClassroomCustomization(models.Model):
    """Model for storing virtual classroom customization settings."""

    classroom = models.OneToOneField(VirtualClassroom, on_delete=models.CASCADE, related_name="customization_settings")
    wall_color = models.CharField(max_length=7, default="#E6E2D7")  # Hex color
    floor_color = models.CharField(max_length=7, default="#C7B299")  # Hex color
    desk_color = models.CharField(max_length=7, default="#8B4513")  # Hex color
    chair_color = models.CharField(max_length=7, default="#4B0082")  # Hex color
    board_color = models.CharField(max_length=7, default="#005C53")  # Hex color
    number_of_rows = models.PositiveIntegerField(default=5)
    desks_per_row = models.PositiveIntegerField(default=6)
    has_plants = models.BooleanField(default=True)
    has_windows = models.BooleanField(default=True)
    has_bookshelf = models.BooleanField(default=True)
    has_clock = models.BooleanField(default=True)
    has_carpet = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Customization for {self.classroom.name}"

    class Meta:
        verbose_name = "Virtual Classroom Customization"
        verbose_name_plural = "Virtual Classroom Customizations"


class VirtualClassroomParticipant(models.Model):
    """Model for tracking active participants in a virtual classroom."""

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    classroom = models.ForeignKey(VirtualClassroom, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    seat_id = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        unique_together = ("classroom", "user")

    def __str__(self):
        return f"{self.user.username} in {self.classroom.name}"

    def to_dict(self):
        return {
            "username": self.user.username,
            "full_name": f"{self.user.first_name} {self.user.last_name}",
            "joined_at": self.joined_at.isoformat(),
            "seat_id": self.seat_id,
            "last_active": self.last_active.isoformat(),
        }


class VirtualClassroomWhiteboard(models.Model):
    """Model to store whiteboard data for each virtual classroom"""

    classroom = models.OneToOneField(VirtualClassroom, on_delete=models.CASCADE, related_name="whiteboard")
    canvas_data = models.JSONField(default=dict, blank=True)
    background_image = models.TextField(blank=True, default="")
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Whiteboard for {self.classroom.name}"

    class Meta:
        ordering = ["-last_updated"]
        verbose_name = "Virtual Classroom Whiteboard"
        verbose_name_plural = "Virtual Classroom Whiteboards"
