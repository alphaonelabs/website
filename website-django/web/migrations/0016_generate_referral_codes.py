# Generated manually

import random
import string
import time

from django.db import migrations


def generate_unique_referral_code():
    """Generate a unique referral code."""
    timestamp = int(time.time())
    random_str = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{timestamp:x}{random_str}"[:8].upper()


def ensure_unique_referral_codes(apps, schema_editor):
    """Generate unique referral codes for all profiles that need them."""
    Profile = apps.get_model("web", "Profile")

    # Get all profiles that need a referral code
    profiles = Profile.objects.filter(referral_code__isnull=True) | Profile.objects.filter(referral_code="")

    # Keep track of used codes
    existing_codes = set(
        Profile.objects.exclude(referral_code__isnull=True)
        .exclude(referral_code="")
        .values_list("referral_code", flat=True)
    )

    for profile in profiles:
        while True:
            code = generate_unique_referral_code()
            if code not in existing_codes:
                profile.referral_code = code
                profile.save()
                existing_codes.add(code)
                break


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0015_profile_referral_code_profile_referral_earnings_and_more"),
    ]

    operations = [
        migrations.RunPython(ensure_unique_referral_codes, reverse_code=migrations.RunPython.noop),
    ]
