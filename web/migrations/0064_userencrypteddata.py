import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import web.encrypted_fields


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0063_virtualclassroom_virtualclassroomcustomization_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserEncryptedData",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("encrypted_email", web.encrypted_fields.EncryptedField(blank=True, default="")),
                ("encrypted_username", web.encrypted_fields.EncryptedField(blank=True, default="")),
                ("email_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("username_hash", models.CharField(blank=True, db_index=True, default="", max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="encrypted_data",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Encrypted Data",
                "verbose_name_plural": "User Encrypted Data",
            },
        ),
    ]
