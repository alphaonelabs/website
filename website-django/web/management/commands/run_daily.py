from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Run daily maintenance tasks"

    def handle(self, *args, **options):
        self.stdout.write(f"Starting daily tasks at {timezone.now()}")

        try:
            # Roll forward sessions
            self.stdout.write("Running roll_forward_sessions...")
            call_command("roll_forward_sessions")
            self.stdout.write(self.style.SUCCESS("Successfully completed roll_forward_sessions"))

            # Send session reminders
            self.stdout.write("Running send_session_reminders...")
            call_command("send_session_reminders")
            self.stdout.write(self.style.SUCCESS("Successfully completed send_session_reminders"))

            # Send verification reminders
            self.stdout.write("Running send_verification_reminders...")
            call_command("send_verification_reminders")
            self.stdout.write(self.style.SUCCESS("Successfully completed send_verification_reminders"))

            # Clean up abandoned drafts
            self.stdout.write("Running cleanup_abandoned_drafts...")
            call_command("cleanup_abandoned_drafts")
            self.stdout.write(self.style.SUCCESS("Successfully completed cleanup_abandoned_drafts"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error running daily tasks: {str(e)}"))
            raise e

        self.stdout.write(self.style.SUCCESS(f"Completed all daily tasks at {timezone.now()}"))
