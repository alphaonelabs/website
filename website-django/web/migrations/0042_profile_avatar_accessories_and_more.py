import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0041_challenge_challenge_type_alter_challenge_week_number_and_more"),
    ]

    operations = [
        # Step 1: Create the Avatar model
        migrations.CreateModel(
            name="Avatar",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("style", models.CharField(default="circle", max_length=50)),
                ("background_color", models.CharField(default="#FFFFFF", max_length=7)),
                ("top", models.CharField(default="short_flat", max_length=50)),
                ("eyebrows", models.CharField(default="default", max_length=50)),
                ("eyes", models.CharField(default="default", max_length=50)),
                ("nose", models.CharField(default="default", max_length=50)),
                ("mouth", models.CharField(default="default", max_length=50)),
                ("facial_hair", models.CharField(default="none", max_length=50)),
                ("skin_color", models.CharField(default="light", max_length=50)),
                ("hair_color", models.CharField(default="#000000", max_length=7)),
                ("accessory", models.CharField(default="none", max_length=50)),
                ("clothing", models.CharField(default="hoodie", max_length=50)),
                ("clothing_color", models.CharField(default="#0000FF", max_length=7)),
                ("svg", models.TextField(blank=True, help_text="Stored SVG string of the custom avatar")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        # Step 2: Add the custom_avatar field to Profile
        migrations.AddField(
            model_name="profile",
            name="custom_avatar",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="profile",
                to="web.avatar",
            ),
        ),
        # Step 3: Update the avatar field
        migrations.AlterField(
            model_name="profile",
            name="avatar",
            field=models.ImageField(blank=True, default="", upload_to="avatars"),
        ),
    ]
