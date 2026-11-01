from django.core.management.base import BaseCommand
from django.utils import timezone

from web.models import Session, SessionEnrollment


class Command(BaseCommand):
    help = "Roll forward sessions that have no enrollments"

    def handle(self, *args, **options):
        now = timezone.now()

        # Get all past sessions with rollover enabled and no enrollments
        sessions = Session.objects.filter(
            enable_rollover=True,
            teacher_confirmed=False,
            start_time__lt=now,
        ).exclude(id__in=SessionEnrollment.objects.values_list("session_id", flat=True))

        rolled_count = 0
        for session in sessions:
            if session.roll_forward():
                session.save()
                rolled_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully rolled forward session "{session.title}" to {session.start_time}')
                )

        if rolled_count == 0:
            self.stdout.write(self.style.SUCCESS("No sessions needed to be rolled forward"))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully rolled forward {rolled_count} sessions"))
