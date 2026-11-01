from django.core.management.base import BaseCommand

from web.notifications import send_verification_reminders


class Command(BaseCommand):
    help = "Sends reminder emails to users who haven’t verified their email."

    def handle(self, *args, **options):
        try:
            send_verification_reminders()
            self.stdout.write(self.style.SUCCESS("Successfully sent verification reminders"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error sending verification reminders: {str(e)}"))
