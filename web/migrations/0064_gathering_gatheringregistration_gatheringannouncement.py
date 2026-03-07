import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0063_virtualclassroom_virtualclassroomcustomization_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Gathering",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, max_length=255, unique=True)),
                ("description", models.TextField()),
                (
                    "gathering_type",
                    models.CharField(
                        choices=[
                            ("meetup", "Meetup"),
                            ("workshop", "Workshop"),
                            ("class", "Class"),
                            ("webinar", "Webinar"),
                            ("conference", "Conference"),
                            ("study_group", "Study Group"),
                            ("networking", "Networking"),
                            ("hackathon", "Hackathon"),
                            ("club_meeting", "Club Meeting"),
                            ("other", "Other"),
                        ],
                        default="meetup",
                        max_length=50,
                    ),
                ),
                ("start_datetime", models.DateTimeField()),
                ("end_datetime", models.DateTimeField()),
                ("is_virtual", models.BooleanField(default=False)),
                ("meeting_link", models.URLField(blank=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                (
                    "latitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                (
                    "longitude",
                    models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
                ),
                (
                    "max_attendees",
                    models.PositiveIntegerField(blank=True, help_text="Leave blank for unlimited", null=True),
                ),
                ("registration_required", models.BooleanField(default=True)),
                (
                    "price",
                    models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
                ),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("private", "Private"),
                            ("invite_only", "Invite Only"),
                        ],
                        default="public",
                        max_length=20,
                    ),
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
                ("image", models.ImageField(blank=True, upload_to="gatherings/")),
                (
                    "tags",
                    models.CharField(blank=True, help_text="Comma-separated tags", max_length=255),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organizer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="organized_gatherings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Gathering",
                "verbose_name_plural": "Gatherings",
                "ordering": ["start_datetime"],
            },
        ),
        migrations.CreateModel(
            name="GatheringRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                            ("waitlisted", "Waitlisted"),
                            ("attended", "Attended"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, help_text="Optional notes from the attendee"),
                ),
                ("registered_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "attendee",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gathering_registrations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "gathering",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="registrations",
                        to="web.gathering",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gathering Registration",
                "verbose_name_plural": "Gathering Registrations",
                "ordering": ["registered_at"],
                "unique_together": {("gathering", "attendee")},
            },
        ),
        migrations.CreateModel(
            name="GatheringAnnouncement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="gathering_announcements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "gathering",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcements",
                        to="web.gathering",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gathering Announcement",
                "verbose_name_plural": "Gathering Announcements",
                "ordering": ["-created_at"],
            },
        ),
    ]
