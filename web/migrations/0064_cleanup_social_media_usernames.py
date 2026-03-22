# Generated migration to clean up social media usernames before enforcing new length constraints

from django.db import migrations


def cleanup_social_media_usernames(apps, schema_editor):
    """
    Clean up social media usernames that exceed new length limits:
    - discord_username: 37 chars (down from 50)
    - slack_username: 21 chars (down from 50)
    - github_username: 39 chars (down from 50)
    
    This migration truncates over-limit usernames to fit the new constraints.
    """
    Profile = apps.get_model("web", "Profile")
    updated_count = 0
    
    for profile in Profile.objects.all():
        modified = False
        
        # Truncate discord_username to 37 chars
        if profile.discord_username and len(profile.discord_username) > 37:
            profile.discord_username = profile.discord_username[:37]
            modified = True
        
        # Truncate slack_username to 21 chars
        if profile.slack_username and len(profile.slack_username) > 21:
            profile.slack_username = profile.slack_username[:21]
            modified = True
        
        # Truncate github_username to 39 chars
        if profile.github_username and len(profile.github_username) > 39:
            profile.github_username = profile.github_username[:39]
            modified = True
        
        if modified:
            # Use update() to bypass validators and Profile.save() with full_clean()
            Profile.objects.filter(pk=profile.pk).update(
                discord_username=profile.discord_username,
                slack_username=profile.slack_username,
                github_username=profile.github_username,
            )
            updated_count += 1
    
    if updated_count > 0:
        print(f"✓ Cleaned up {updated_count} profiles with over-limit usernames")


def reverse_cleanup(apps, schema_editor):
    """
    Reverse migration - no action needed as truncation is one-way.
    Original usernames are lost, so we cannot restore them.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0063_virtualclassroom_virtualclassroomcustomization_and_more"),
    ]

    operations = [
        migrations.RunPython(cleanup_social_media_usernames, reverse_cleanup),
    ]
