"""
Tests for custom validators used in the Alpha One Labs platform.

Tests for social media username validators (Discord, Slack, GitHub).
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from web.forms import ProfileUpdateForm
from web.models import Profile
from web.validators import validate_discord_username, validate_github_username, validate_slack_username

User = get_user_model()


class DiscordUsernameValidatorTests(TestCase):
    """Test cases for Discord username validation."""

    def test_valid_discord_username(self):
        """Test valid Discord usernames."""
        valid_usernames = [
            "User",
            "User123",
            "user_name",
            "user-name",
            "user.name",
            "User#1234",
            "ValidUser123",
        ]
        for username in valid_usernames:
            with self.subTest(username=username):
                try:
                    validate_discord_username(username)
                except ValidationError:
                    self.fail(f"'{username}' should be valid, but raised ValidationError")

    def test_discord_username_too_short(self):
        """Test Discord username shorter than 2 characters."""
        with self.assertRaises(ValidationError) as cm:
            validate_discord_username("A")
        self.assertIn("2 and 32", str(cm.exception))

    def test_discord_username_too_long(self):
        """Test Discord username longer than 32 characters."""
        long_username = "A" * 33
        with self.assertRaises(ValidationError) as cm:
            validate_discord_username(long_username)
        self.assertIn("2 and 32", str(cm.exception))

    def test_discord_username_invalid_characters(self):
        """Test Discord username with invalid characters."""
        invalid_usernames = [
            "User Name",  # spaces
            "User@Name",  # @
            "User!",  # !
            "User$",  # $
        ]
        for username in invalid_usernames:
            with self.subTest(username=username):
                with self.assertRaises(ValidationError):
                    validate_discord_username(username)

    def test_empty_discord_username(self):
        """Test that empty Discord username is allowed."""
        # Empty values should be allowed (use blank=True in model)
        validate_discord_username("")  # Should not raise


class SlackUsernameValidatorTests(TestCase):
    """Test cases for Slack username validation."""

    def test_valid_slack_username(self):
        """Test valid Slack usernames."""
        valid_usernames = [
            "john",
            "john.doe",
            "john-doe",
            "john_doe",
            "a",
            "user123",
        ]
        for username in valid_usernames:
            with self.subTest(username=username):
                try:
                    validate_slack_username(username)
                except ValidationError:
                    self.fail(f"'{username}' should be valid, but raised ValidationError")

    def test_slack_username_too_long(self):
        """Test Slack username longer than 21 characters."""
        long_username = "a" * 22
        with self.assertRaises(ValidationError) as cm:
            validate_slack_username(long_username)
        self.assertIn("1 and 21", str(cm.exception))

    def test_slack_username_starts_with_number(self):
        """Test Slack username starting with a number."""
        with self.assertRaises(ValidationError):
            validate_slack_username("123user")

    def test_slack_username_starts_with_hyphen(self):
        """Test Slack username starting with a hyphen."""
        with self.assertRaises(ValidationError):
            validate_slack_username("-user")

    def test_slack_username_uppercase(self):
        """Test Slack username with uppercase letters."""
        with self.assertRaises(ValidationError):
            validate_slack_username("User")

    def test_slack_username_with_spaces(self):
        """Test Slack username with spaces."""
        with self.assertRaises(ValidationError):
            validate_slack_username("user name")

    def test_empty_slack_username(self):
        """Test that empty Slack username is allowed."""
        validate_slack_username("")  # Should not raise


class GitHubUsernameValidatorTests(TestCase):
    """Test cases for GitHub username validation."""

    def test_valid_github_username(self):
        """Test valid GitHub usernames."""
        valid_usernames = [
            "octocat",
            "octo-cat",
            "octocat123",
            "a",
            "github-user",
            "github123user",
        ]
        for username in valid_usernames:
            with self.subTest(username=username):
                try:
                    validate_github_username(username)
                except ValidationError:
                    self.fail(f"'{username}' should be valid, but raised ValidationError")

    def test_github_username_too_long(self):
        """Test GitHub username longer than 39 characters."""
        long_username = "a" * 40
        with self.assertRaises(ValidationError) as cm:
            validate_github_username(long_username)
        self.assertIn("1 and 39", str(cm.exception))

    def test_github_username_starts_with_hyphen(self):
        """Test GitHub username starting with a hyphen."""
        with self.assertRaises(ValidationError):
            validate_github_username("-octocat")

    def test_github_username_ends_with_hyphen(self):
        """Test GitHub username ending with a hyphen."""
        with self.assertRaises(ValidationError):
            validate_github_username("octocat-")

    def test_github_username_with_spaces(self):
        """Test GitHub username with spaces."""
        with self.assertRaises(ValidationError):
            validate_github_username("octo cat")

    def test_github_username_with_underscore(self):
        """Test GitHub username with underscore (not allowed)."""
        with self.assertRaises(ValidationError):
            validate_github_username("octo_cat")

    def test_github_username_with_dots(self):
        """Test GitHub username with dots (not allowed)."""
        with self.assertRaises(ValidationError):
            validate_github_username("octo.cat")

    def test_empty_github_username(self):
        """Test that empty GitHub username is allowed."""
        validate_github_username("")  # Should not raise


class ProfileModelValidationTests(TestCase):
    """Test Profile model validation with validators."""

    def setUp(self):
        """Create a test user."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_profile_with_valid_social_usernames(self):
        """Test creating a profile with valid social media usernames."""
        profile = Profile.objects.create(
            user=self.user,
            discord_username="TestUser#1234",
            slack_username="test.user",
            github_username="test-user",
        )
        profile.full_clean()  # Should not raise
        self.assertEqual(profile.discord_username, "TestUser#1234")

    def test_profile_with_invalid_discord_username(self):
        """Test creating a profile with invalid Discord username."""
        profile = Profile.objects.create(
            user=self.user,
            discord_username="A",  # Too short
            slack_username="valid",
            github_username="valid",
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_with_invalid_slack_username(self):
        """Test creating a profile with invalid Slack username."""
        profile = Profile.objects.create(
            user=self.user,
            discord_username="ValidUser",
            slack_username="123invalid",  # Starts with number
            github_username="valid",
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_with_invalid_github_username(self):
        """Test creating a profile with invalid GitHub username."""
        profile = Profile.objects.create(
            user=self.user,
            discord_username="ValidUser",
            slack_username="valid",
            github_username="-invalid",  # Starts with hyphen
        )
        with self.assertRaises(ValidationError):
            profile.full_clean()


class ProfileUpdateFormValidationTests(TestCase):
    """Test ProfileUpdateForm validation with social media fields."""

    def setUp(self):
        """Create a test user."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.user.profile.save()

    def test_form_with_valid_social_usernames(self):
        """Test form with valid social media usernames."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "bio": "Test bio",
            "expertise": "Python",
            "is_profile_public": "True",
            "discord_username": "TestUser#1234",
            "slack_username": "test.user",
            "github_username": "test-user",
        }
        form = ProfileUpdateForm(form_data, instance=self.user)
        self.assertTrue(form.is_valid())

    def test_form_with_invalid_discord_username(self):
        """Test form with invalid Discord username."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "bio": "Test bio",
            "expertise": "Python",
            "is_profile_public": "True",
            "discord_username": "A",  # Too short
            "slack_username": "",
            "github_username": "",
        }
        form = ProfileUpdateForm(form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("discord_username", form.errors)

    def test_form_with_invalid_slack_username(self):
        """Test form with invalid Slack username."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "bio": "Test bio",
            "expertise": "Python",
            "is_profile_public": "True",
            "discord_username": "",
            "slack_username": "123invalid",  # Starts with number
            "github_username": "",
        }
        form = ProfileUpdateForm(form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("slack_username", form.errors)

    def test_form_with_invalid_github_username(self):
        """Test form with invalid GitHub username."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "bio": "Test bio",
            "expertise": "Python",
            "is_profile_public": "True",
            "discord_username": "",
            "slack_username": "",
            "github_username": "-invalid",  # Starts with hyphen
        }
        form = ProfileUpdateForm(form_data, instance=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn("github_username", form.errors)

    def test_form_with_empty_social_usernames(self):
        """Test form with empty social media usernames."""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "",
            "last_name": "",
            "bio": "Test bio",
            "expertise": "Python",
            "is_profile_public": "False",
            "discord_username": "",
            "slack_username": "",
            "github_username": "",
        }
        form = ProfileUpdateForm(form_data, instance=self.user)
        self.assertTrue(form.is_valid())
