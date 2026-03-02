from django.db import migrations, models


PRIORITY_RANK_MAP = {"high": 3, "medium": 2, "low": 1}


def backfill_priority_rank(apps, schema_editor):
    StudyPlanItem = apps.get_model("web", "StudyPlanItem")
    for item in StudyPlanItem.objects.all().iterator():
        item.priority_rank = PRIORITY_RANK_MAP.get(item.priority, 2)
        item.save(update_fields=["priority_rank"])


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0064_add_learning_analytics_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="studyplanitem",
            name="priority_rank",
            field=models.PositiveIntegerField(default=2),
        ),
        migrations.RunPython(backfill_priority_rank, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="studyplanitem",
            options={"ordering": ["order", "-priority_rank", "due_date"]},
        ),
    ]
