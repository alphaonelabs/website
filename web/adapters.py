import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter to handle social account signups and profile creation."""

    def pre_social_login(self, request, sociallogin):
        """
        Connect social login to existing account if emails match.

        When a user signs up with email/password first, then later tries
        to log in with Google/GitHub using the same email, this links
        the social account to the existing user instead of creating a duplicate.
        """
        if sociallogin.is_existing:
            return

        email = None
        if sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get("email")

        if not email:
            email_addresses = sociallogin.email_addresses
            if email_addresses:
                email = email_addresses[0].email

        if email:
            try:
                user = User.objects.get(email=email)
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass

    def populate_user(self, request, sociallogin, data):
        """Populate user fields from social account data."""
        user = super().populate_user(request, sociallogin, data)

        # Ensure first_name and last_name are set from social provider data
        if not user.first_name:
            user.first_name = data.get("first_name", "")
        if not user.last_name:
            user.last_name = data.get("last_name", "")

        return user

    def save_user(self, request, sociallogin, form=None):
        """Save user and ensure profile is properly set up after social signup."""
        user = super().save_user(request, sociallogin, form)

        # Ensure profile exists and set defaults for social signups
        if hasattr(user, "profile"):
            profile = user.profile
            # Social signups default to private profile and student role
            if not profile.is_profile_public:
                profile.is_profile_public = False
            profile.save()

        return user
