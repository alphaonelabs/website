import django.db.models.deletion
import markdownx.models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("web", "0063_virtualclassroom_virtualclassroomcustomization_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="DocumentationNoteTopic",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255, unique=True)),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "icon",
                    models.CharField(
                        default="book",
                        help_text="Icon class name (e.g., 'book', 'beaker', 'calculator')",
                        max_length=50,
                    ),
                ),
                (
                    "color",
                    models.CharField(
                        default="teal",
                        help_text="Tailwind color class (e.g., 'teal', 'blue', 'purple')",
                        max_length=20,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0, help_text="Display order in lists")),
                ("is_published", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Documentation Note Topic",
                "verbose_name_plural": "Documentation Note Topics",
                "ordering": ["order", "title"],
            },
        ),
        migrations.CreateModel(
            name="DocumentationNoteSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField()),
                ("description", models.CharField(blank=True, max_length=500)),
                ("order", models.PositiveIntegerField(default=0, help_text="Display order within topic")),
                (
                    "icon",
                    models.CharField(blank=True, help_text="Optional icon for section navigation", max_length=50),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "topic",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sections",
                        to="web.documentationnotetopic",
                    ),
                ),
            ],
            options={
                "verbose_name": "Documentation Note Section",
                "verbose_name_plural": "Documentation Note Sections",
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="DocumentationNoteProgress",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "completion_percentage",
                    models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(100)]),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_accessed_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "current_section",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="viewing_users",
                        to="web.documentationnotesection",
                    ),
                ),
                (
                    "topic",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="web.documentationnotetopic"),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="note_progress",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Documentation Note Progress",
                "verbose_name_plural": "Documentation Note Progress",
            },
        ),
        migrations.CreateModel(
            name="DocumentationNoteContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "markdown_content",
                    markdownx.models.MarkdownxField(help_text="Supports Markdown formatting with LaTeX math support"),
                ),
                ("html_content", models.TextField(blank=True, editable=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "last_edited_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "section",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="content",
                        to="web.documentationnotesection",
                    ),
                ),
            ],
            options={
                "verbose_name": "Documentation Note Content",
                "verbose_name_plural": "Documentation Note Contents",
            },
        ),
        migrations.AddField(
            model_name="documentationnoteprogress",
            name="sections_viewed",
            field=models.ManyToManyField(
                blank=True, help_text="Sections the user has viewed", to="web.documentationnotesection"
            ),
        ),
        migrations.AddIndex(
            model_name="documentationnotetopic",
            index=models.Index(fields=["slug"], name="web_document_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="documentationnotetopic",
            index=models.Index(fields=["is_published"], name="web_document_published_idx"),
        ),
        migrations.AddIndex(
            model_name="documentationnotesection",
            index=models.Index(fields=["topic", "order"], name="web_document_section_order_idx"),
        ),
        migrations.AddIndex(
            model_name="documentationnoteprogress",
            index=models.Index(fields=["user", "topic"], name="web_document_progress_user_topic_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="documentationnotesection",
            unique_together={("topic", "slug")},
        ),
        migrations.AlterUniqueTogether(
            name="documentationnoteprogress",
            unique_together={("user", "topic")},
        ),
    ]
