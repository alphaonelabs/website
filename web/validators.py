"""
Custom validators for Alpha One Labs Education Platform.

Validates usernames across various social media platforms.
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_discord_username(value):
    """
    Validate Discord username format.

    Discord usernames:
    - Must be 2-32 characters long
    - Can contain letters, numbers, underscores, hyphens, and dots
    - Cannot contain spaces
    """
    if not value:
        return  # Allow empty values; use blank=True in model if needed

    # Remove the discriminator (e.g., "User#1234")
    if "#" in value:
        username_part = value.split("#")[0]
    else:
        username_part = value

    if len(username_part) < 2 or len(username_part) > 32:
        raise ValidationError(
            _("Discord username must be between 2 and 32 characters long (excluding discriminator)."),
            code="invalid_discord_length",
        )

    # Discord usernames can contain letters, numbers, underscores, hyphens, and dots
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username_part):
        raise ValidationError(
            _("Discord username can only contain letters, numbers, underscores, hyphens, and dots."),
            code="invalid_discord_chars",
        )


def validate_slack_username(value):
    """
    Validate Slack username format.

    Slack usernames:
    - Must be 1-21 characters long
    - Can only contain lowercase letters, numbers, periods, hyphens, and underscores
    - Must start with a letter
    """
    if not value:
        return

    if len(value) < 1 or len(value) > 21:
        raise ValidationError(
            _("Slack username must be between 1 and 21 characters long."),
            code="invalid_slack_length",
        )

    if not re.match(r"^[a-z][a-z0-9._-]*$", value):
        raise ValidationError(
            _(
                "Slack username must start with a letter and can only contain "
                "lowercase letters, numbers, periods, hyphens, and underscores."
            ),
            code="invalid_slack_chars",
        )


def validate_github_username(value):
    """
    Validate GitHub username format.

    GitHub usernames:
    - Must be 1-39 characters long
    - Can only contain alphanumeric characters and hyphens
    - Cannot start or end with a hyphen
    """
    if not value:
        return

    if len(value) < 1 or len(value) > 39:
        raise ValidationError(
            _("GitHub username must be between 1 and 39 characters long."),
            code="invalid_github_length",
        )

    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", value):
        raise ValidationError(
            _(
                "GitHub username can only contain alphanumeric characters and hyphens, "
                "and cannot start or end with a hyphen."
            ),
            code="invalid_github_chars",
        )
