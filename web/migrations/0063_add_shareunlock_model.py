# Generated migration for ShareUnlock feature

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0062_update_waitingroom_for_sessions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="coursematerial",
            name="unlock_by_sharing",
            field=models.BooleanField(
                default=False, help_text="If True, users must share to unlock this bonus material"
            ),
        ),
        migrations.AddField(
            model_name="coursematerial",
            name="shares_required",
            field=models.PositiveIntegerField(default=1, help_text="Number of shares required to unlock this material"),
        ),
        migrations.CreateModel(
            name="ShareUnlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("share_token", models.CharField(max_length=32, unique=True)),
                ("shared_at", models.DateTimeField(auto_now_add=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("is_verified", models.BooleanField(default=False)),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("twitter", "Twitter"),
                            ("facebook", "Facebook"),
                            ("linkedin", "LinkedIn"),
                            ("email", "Email"),
                            ("other", "Other"),
                        ],
                        default="twitter",
                        max_length=20,
                    ),
                ),
                (
                    "material",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="share_unlocks",
                        to="web.coursematerial",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="share_unlocks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-shared_at"],
            },
        ),
        migrations.AddIndex(
            model_name="shareunlock",
            index=models.Index(fields=["user", "material"], name="web_shareun_user_id_8a9b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="shareunlock",
            index=models.Index(fields=["share_token"], name="web_shareun_share_t_3f8e1d_idx"),
        ),
    ]
