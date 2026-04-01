from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0065_studyplanitem_priority_rank"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="studyplan",
            constraint=models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="unique_active_studyplan_per_user",
            ),
        ),
    ]
