from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from web.models import Course


class Command(BaseCommand):
    help = "Deletes abandoned draft courses older than 30 days for unverified users."

    def handle(self, *args, **options):
        try:
            # Define the cutoff date (30 days ago)
            cutoff_date = timezone.now() - timedelta(days=30)

            # Find draft courses for unverified users older than the cutoff date
            abandoned_drafts = Course.objects.filter(
                teacher__emailaddress__verified=False,
                teacher__emailaddress__created__lt=cutoff_date,
                status="draft",
                created_at__lt=cutoff_date,
            ).select_related("teacher")

            # Log and delete the abandoned drafts
            count = abandoned_drafts.count()
            if count > 0:
                draft_ids = list(abandoned_drafts.values_list("id", flat=True))
                self.stdout.write(f"Deleting abandoned drafts with IDs: {draft_ids}")
                abandoned_drafts.delete()

            self.stdout.write(self.style.SUCCESS(f"Successfully deleted {count} abandoned draft courses"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cleaning up abandoned drafts: {str(e)}"))
