from django.core.management.base import BaseCommand

from web.notifications import send_weekly_progress_updates


class Command(BaseCommand):
    help = "Send weekly progress updates to enrolled students"

    def handle(self, *args, **options):
        try:
            send_weekly_progress_updates()
            self.stdout.write(self.style.SUCCESS("Successfully sent weekly progress updates"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending weekly progress updates: {str(e)}"))
