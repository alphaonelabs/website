from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from web.encrypted_fields import make_hash
from web.models import UserEncryptedData

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Populate (or refresh) the UserEncryptedData shadow table for existing users. "
        "Run this once after applying migration 0064_userencrypteddata to back-fill "
        "encrypted email/username and their HMAC-SHA256 lookup hashes for all users "
        "that were created before the encryption shadow table existed."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Number of users to process per database batch (default: 500).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        total = User.objects.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No users found — nothing to populate."))
            return

        self.stdout.write(f"Processing {total} user(s) in batches of {batch_size}…")

        created = updated = errors = processed = 0

        for user in User.objects.iterator(chunk_size=batch_size):
            email = (user.email or "").strip()
            username = (user.username or "").strip()
            try:
                _, was_created = UserEncryptedData.objects.update_or_create(
                    user=user,
                    defaults={
                        "encrypted_email": user.email,
                        "encrypted_username": user.username,
                        "email_hash": make_hash(email) if email else "",
                        "username_hash": make_hash(username) if username else "",
                    },
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            except Exception as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(f"  Error processing user id={user.pk}: {exc}"))

            processed += 1
            if processed % batch_size == 0:
                self.stdout.write(f"  Processed {processed}/{total}…")

        self.stdout.write(self.style.SUCCESS(f"Done. Created: {created}, Updated: {updated}, Errors: {errors}."))
