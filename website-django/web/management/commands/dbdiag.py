import json

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

try:
    from web.models import Course, Enrollment
except Exception:  # pragma: no cover - if migrations not applied yet
    Course = None  # type: ignore
    Enrollment = None  # type: ignore


class Command(BaseCommand):
    help = "Print database configuration & key data counts to verify runtime state"

    def handle(self, *args, **options):
        db_cfg = connection.settings_dict.copy()
        redacted = db_cfg.copy()
        # Remove sensitive fields
        for k in ["PASSWORD", "OPTIONS"]:
            if k in redacted:
                redacted[k] = "***" if k == "PASSWORD" else redacted[k]

        self.stdout.write("Runtime DEBUG=%s" % settings.DEBUG)
        self.stdout.write("Database settings (sanitized):")
        self.stdout.write(
            json.dumps({k: redacted[k] for k in ["ENGINE", "NAME", "HOST", "PORT", "USER"] if k in redacted}, indent=2)
        )

        # Low-level sanity query
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            self.stdout.write("Basic connectivity check: %s" % cur.fetchone())

        if Course is None:
            self.stdout.write(self.style.WARNING("Course model not importable yet (migrations?)"))
            return

        total_courses = Course.objects.count()
        published_featured = Course.objects.filter(status="published", is_featured=True).count()
        enrollments = Enrollment.objects.count() if Enrollment else 0

        self.stdout.write(f"Course count: {total_courses}")
        self.stdout.write(f"Published + featured courses: {published_featured}")
        self.stdout.write(f"Enrollment count: {enrollments}")

        sample = list(
            Course.objects.filter(status="published", is_featured=True)
            .order_by("-created_at")
            .values("id", "title", "status", "is_featured")[:5]
        )
        self.stdout.write("Sample featured courses: %s" % json.dumps(sample, indent=2))

        # Show which database the ORM believes it is using (alias + vendor)
        self.stdout.write(f"Connection alias: {connection.alias}; vendor: {connection.vendor}")

        # Confirm table name resolution for Course
        self.stdout.write(f"Course db table: {Course._meta.db_table}")

        self.stdout.write(self.style.SUCCESS("dbdiag complete"))
