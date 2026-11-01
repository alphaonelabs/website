from django.core.management.base import BaseCommand

from web.notifications import send_upcoming_session_reminders


class Command(BaseCommand):
    help = "Send reminders for upcoming sessions in the next 24 hours"

    def handle(self, *args, **options):
        try:
            send_upcoming_session_reminders()
            self.stdout.write(self.style.SUCCESS("Successfully sent session reminders"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending session reminders: {str(e)}"))
