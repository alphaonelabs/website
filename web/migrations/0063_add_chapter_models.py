# Generated migration for chapter models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0062_update_waitingroom_for_sessions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Chapter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "name",
                    models.CharField(help_text="Chapter name (e.g., 'Alpha One Seattle')", max_length=200),
                ),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                (
                    "description",
                    models.TextField(help_text="Description of the chapter's mission and activities"),
                ),
                ("region", models.CharField(help_text="City, region, or area (e.g., 'Seattle, WA')", max_length=200)),
                ("country", models.CharField(blank=True, default="", max_length=100)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                (
                    "meeting_schedule",
                    models.TextField(blank=True, help_text="Proposed meeting schedule or format"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Approval"),
                            ("active", "Active"),
                            ("inactive", "Inactive"),
                            ("suspended", "Suspended"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="chapters/")),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("website", models.URLField(blank=True)),
                (
                    "social_links",
                    models.JSONField(blank=True, default=dict, help_text="Social media links"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_chapters",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ChapterMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("leader", "Chapter Lead"),
                            ("co_organizer", "Co-Organizer"),
                            ("volunteer", "Volunteer"),
                            ("participant", "Participant"),
                        ],
                        default="participant",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chapter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="memberships",
                        to="web.chapter",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chapter_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-joined_at"],
                "unique_together": {("chapter", "user")},
            },
        ),
        migrations.CreateModel(
            name="ChapterEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("slug", models.SlugField(blank=True, max_length=200)),
                ("description", models.TextField()),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("workshop", "Workshop"),
                            ("meetup", "Meetup"),
                            ("training", "Teacher Training"),
                            ("showcase", "Student Showcase"),
                            ("talk", "Guest Speaker Talk"),
                            ("hackathon", "Educational Hackathon"),
                            ("other", "Other"),
                        ],
                        default="meetup",
                        max_length=20,
                    ),
                ),
                ("start_datetime", models.DateTimeField()),
                ("end_datetime", models.DateTimeField()),
                ("location", models.CharField(help_text="Physical or virtual location", max_length=300)),
                ("is_virtual", models.BooleanField(default=False)),
                ("virtual_link", models.URLField(blank=True, help_text="Link for virtual events")),
                (
                    "max_attendees",
                    models.PositiveIntegerField(blank=True, help_text="Leave blank for unlimited", null=True),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("cancelled", "Cancelled"),
                            ("completed", "Completed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("image", models.ImageField(blank=True, null=True, upload_to="chapter_events/")),
                (
                    "chapter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="web.chapter",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_chapter_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["start_datetime"],
            },
        ),
        migrations.CreateModel(
            name="ChapterEventRSVP",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("confirmed", "Confirmed"),
                            ("maybe", "Maybe"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="confirmed",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rsvps",
                        to="web.chapterevent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chapter_event_rsvps",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("event", "user")},
            },
        ),
        migrations.CreateModel(
            name="ChapterApplication",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chapter_name", models.CharField(max_length=200)),
                ("region", models.CharField(max_length=200)),
                ("country", models.CharField(blank=True, default="", max_length=100)),
                ("description", models.TextField(help_text="Describe your vision for the chapter")),
                ("proposed_schedule", models.TextField(help_text="Proposed meeting schedule")),
                (
                    "experience",
                    models.TextField(help_text="Your relevant experience in education or community organizing"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Review"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("review_notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chapter_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_applications",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
