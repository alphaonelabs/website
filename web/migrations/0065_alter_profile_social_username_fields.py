# Schema migration to enforce new field length constraints on social media usernames

from django.db import migrations, models
import web.validators


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0064_cleanup_social_media_usernames"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="discord_username",
            field=models.CharField(
                blank=True,
                help_text="Your Discord username (e.g., User#1234)",
                max_length=37,
                validators=[web.validators.validate_discord_username],
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="slack_username",
            field=models.CharField(
                blank=True,
                help_text="Your Slack username",
                max_length=21,
                validators=[web.validators.validate_slack_username],
            ),
        ),
        migrations.AlterField(
            model_name="profile",
            name="github_username",
            field=models.CharField(
                blank=True,
                help_text="Your GitHub username (without @)",
                max_length=39,
                validators=[web.validators.validate_github_username],
            ),
        ),
    ]
