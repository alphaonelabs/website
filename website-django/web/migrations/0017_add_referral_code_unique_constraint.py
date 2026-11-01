# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0016_generate_referral_codes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="referral_code",
            field=models.CharField(blank=True, max_length=20, unique=True),
        ),
    ]
