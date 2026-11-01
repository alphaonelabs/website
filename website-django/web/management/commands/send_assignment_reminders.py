# web/management/commands/send_assignment_reminders.py
from django.core.management.base import BaseCommand

from web.notifications import send_assignment_reminders


class Command(BaseCommand):
    help = "Send reminders for upcoming assignment deadlines"

    def handle(self, *args, **options):
        try:
            send_assignment_reminders()
            self.stdout.write(self.style.SUCCESS("Successfully sent assignment reminders"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending assignment reminders: {str(e)}"))
