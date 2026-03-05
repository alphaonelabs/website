# Generated manually for infographics and lesson summaries feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0062_update_waitingroom_for_sessions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Infographic",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(help_text="Title of the infographic", max_length=200),
                ),
                ("content", models.TextField(help_text="Main content or fact to display")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("tip", "Educational Tip"),
                            ("fact", "Did You Know?"),
                            ("summary", "Quick Summary"),
                            ("guide", "How-To Guide"),
                        ],
                        default="tip",
                        max_length=20,
                    ),
                ),
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Optional background image",
                        upload_to="infographics/",
                    ),
                ),
                (
                    "background_color",
                    models.CharField(
                        default="#5EEAD4",
                        help_text="Hex color for background (e.g., #5EEAD4 for teal-300)",
                        max_length=7,
                    ),
                ),
                (
                    "text_color",
                    models.CharField(
                        default="#1F2937",
                        help_text="Hex color for text (e.g., #1F2937)",
                        max_length=7,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_published", models.BooleanField(default=True)),
                ("views", models.IntegerField(default=0)),
                ("shares", models.IntegerField(default=0)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="infographics",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="infographics",
                        to="web.subject",
                    ),
                ),
            ],
            options={
                "verbose_name": "Infographic",
                "verbose_name_plural": "Infographics",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="LessonSummary",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "title",
                    models.CharField(help_text="Title of the lesson summary", max_length=200),
                ),
                (
                    "key_learnings",
                    models.TextField(help_text="Main points learned (one per line)"),
                ),
                (
                    "additional_notes",
                    models.TextField(blank=True, help_text="Additional notes or thoughts"),
                ),
                ("date", models.DateField(default=django.utils.timezone.now)),
                (
                    "background_style",
                    models.CharField(
                        choices=[
                            ("gradient1", "Teal Gradient"),
                            ("gradient2", "Blue Gradient"),
                            ("gradient3", "Purple Gradient"),
                            ("solid", "Solid Color"),
                        ],
                        default="gradient1",
                        max_length=20,
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=False,
                        help_text="Make this summary public for others to see",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_summaries",
                        to="web.course",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_summaries",
                        to="web.session",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lesson_summaries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Lesson Summary",
                "verbose_name_plural": "Lesson Summaries",
                "ordering": ["-date", "-created_at"],
            },
        ),
    ]
