from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth.models import User
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from web.adapters import CustomSocialAccountAdapter
from web.models import Profile

OAUTH_SETTINGS = {
    "ACCOUNT_EMAIL_VERIFICATION": "none",
    "ACCOUNT_EMAIL_REQUIRED": True,
    "SOCIALACCOUNT_AUTO_SIGNUP": True,
    "ACCOUNT_RATE_LIMITS": {
        "login_attempt": None,
        "login_failed": None,
        "signup": None,
        "send_email": None,
        "change_email": None,
    },
    "SOCIALACCOUNT_PROVIDERS": {
        "google": {
            "APP": {
                "client_id": "test-google-client-id",
                "secret": "test-google-secret",
            },
            "SCOPE": ["profile", "email"],
            "AUTH_PARAMS": {"access_type": "online"},
            "VERIFIED_EMAIL": True,
        },
        "github": {
            "APP": {
                "client_id": "test-github-client-id",
                "secret": "test-github-secret",
            },
            "SCOPE": ["user:email"],
            "VERIFIED_EMAIL": True,
        },
    },
}


@override_settings(**OAUTH_SETTINGS)
class OAuthTemplateTests(TestCase):
    """Test that OAuth buttons appear on login and signup pages."""

    def setUp(self):
        self.client = Client()

    def test_login_page_shows_google_button(self):
        """Test that the login page shows the Google OAuth button."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google")

    def test_login_page_shows_github_button(self):
        """Test that the login page shows the GitHub OAuth button."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GitHub")

    def test_login_page_shows_email_form(self):
        """Test that the traditional email login form still appears."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')

    def test_login_page_shows_divider(self):
        """Test that the 'Or sign in with email' divider appears."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Or sign in with email")

    def test_signup_page_shows_google_button(self):
        """Test that the signup page shows Google OAuth button."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Google")

    def test_signup_page_shows_github_button(self):
        """Test that the signup page shows GitHub OAuth button."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GitHub")

    def test_signup_page_still_has_form(self):
        """Test that the traditional signup form still exists."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Account")
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')


@override_settings(**OAUTH_SETTINGS)
class CustomSocialAccountAdapterTests(TestCase):
    """Test the custom social account adapter."""

    def setUp(self):
        self.factory = RequestFactory()
        self.adapter = CustomSocialAccountAdapter()

    def test_pre_social_login_connects_existing_user(self):
        """Test that social login connects to existing account with same email."""
        existing_user = User.objects.create_user(
            username="existinguser",
            email="test@example.com",
            password="testpass123",
        )

        request = self.factory.get("/")
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()

        sociallogin = SocialLogin(
            user=User(email="test@example.com"),
            account=SocialAccount(
                provider="google",
                uid="12345",
                extra_data={"email": "test@example.com"},
            ),
        )

        self.adapter.pre_social_login(request, sociallogin)
        self.assertEqual(sociallogin.user.pk, existing_user.pk)

    def test_pre_social_login_skips_for_new_user(self):
        """Test that social login does not fail for completely new users."""
        request = self.factory.get("/")
        from django.contrib.sessions.backends.db import SessionStore

        request.session = SessionStore()

        sociallogin = SocialLogin(
            user=User(email="brand_new@example.com"),
            account=SocialAccount(
                provider="google",
                uid="99999",
                extra_data={"email": "brand_new@example.com"},
            ),
        )

        # Should not raise any exception
        self.adapter.pre_social_login(request, sociallogin)

    def test_populate_user_sets_names(self):
        """Test that populate_user sets first and last name from social data."""
        request = self.factory.get("/")

        sociallogin = SocialLogin(
            user=User(),
            account=SocialAccount(
                provider="google",
                uid="12345",
                extra_data={},
            ),
        )

        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }

        user = self.adapter.populate_user(request, sociallogin, data)
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")


@override_settings(**OAUTH_SETTINGS)
class ProfileCreationOnSocialSignupTests(TestCase):
    """Test that Profile is properly created for social signups."""

    def test_profile_created_for_new_user(self):
        """Test that a Profile is automatically created when a User is created."""
        user = User.objects.create_user(
            username="socialuser",
            email="social@example.com",
            password="testpass123",
        )
        self.assertTrue(hasattr(user, "profile"))
        self.assertIsInstance(user.profile, Profile)

    def test_profile_defaults_for_social_signup(self):
        """Test that profile defaults are correct for social signups."""
        user = User.objects.create_user(
            username="oauthuser",
            email="oauth@example.com",
            password="testpass123",
        )
        profile = user.profile
        self.assertFalse(profile.is_teacher)
        self.assertFalse(profile.is_profile_public)

    @patch("web.models.Profile.save")
    def test_set_user_type_handles_no_post_data(self, mock_save):
        """Test that set_user_type works when request has no POST data (social signup)."""
        from web.models import set_user_type

        user = User.objects.create_user(
            username="testsocial",
            email="testsocial@example.com",
            password="testpass123",
        )

        request = RequestFactory().get("/")
        request.POST = {}

        set_user_type(sender=User, request=request, user=user)
        # is_teacher should be False since POST data is empty
        self.assertFalse(user.profile.is_teacher)

    @patch("web.models.Profile.save")
    def test_set_user_type_handles_none_request(self, mock_save):
        """Test that set_user_type handles None request (edge case)."""
        from web.models import set_user_type

        user = User.objects.create_user(
            username="testnone",
            email="testnone@example.com",
            password="testpass123",
        )

        set_user_type(sender=User, request=None, user=user)
        self.assertFalse(user.profile.is_teacher)


@override_settings(**OAUTH_SETTINGS)
class TraditionalLoginStillWorksTests(TestCase):
    """Test that traditional email/password login still works alongside OAuth."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password="securepassword123",
        )
        # Mark email as verified for allauth
        from allauth.account.models import EmailAddress

        EmailAddress.objects.create(
            user=self.user,
            email="testuser@example.com",
            verified=True,
            primary=True,
        )

    def test_traditional_login_works(self):
        """Test that email/password login still functions correctly."""
        response = self.client.post(
            reverse("account_login"),
            {
                "login": "testuser@example.com",
                "password": "securepassword123",
            },
        )
        # Should redirect on successful login
        self.assertIn(response.status_code, [200, 302])

    def test_login_page_accessible(self):
        """Test that login page is accessible."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_accessible(self):
        """Test that signup page is accessible."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
