from typing import Any

from django.core.management.base import BaseCommand

from web.models import PeerMessage
from web.secure_messaging import MESSAGE_RETENTION_DAYS, get_message_retention_cutoff


class Command(BaseCommand):
    """Management command to delete peer messages older than the retention period."""

    help = f"Deletes direct messages older than {MESSAGE_RETENTION_DAYS} days."

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Execute the management command to remove expired messages.

        Deletes all PeerMessage records created before the retention cutoff
        and reports the count of deleted messages to stdout.
        """
        cutoff = get_message_retention_cutoff()
        expired_qs = PeerMessage.objects.filter(created_at__lt=cutoff)
        deleted_count, _ = expired_qs.delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} expired messages"))
