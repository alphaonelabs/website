from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import Client, TestCase, override_settings
from django.urls import reverse

# Mock staticfiles_storage.url to avoid static files issues
original_url = staticfiles_storage.url
staticfiles_storage.url = lambda path: f"/static/{path}"


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=False,
    ACCOUNT_AUTHENTICATION_METHOD="email",
    ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE=True,
    ACCOUNT_RATE_LIMITS={  # Disable rate limiting for tests
        "login_attempt": None,
        "login_failed": None,
        "signup": None,
        "send_email": None,
        "change_email": None,
    },
)
class SignupFormTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.signup_url = reverse("account_signup")
        # Mock captcha validation
        patcher = patch("captcha.fields.CaptchaField.clean", return_value=True)
        self.mock_captcha = patcher.start()
        self.addCleanup(patcher.stop)

        # Create a user with a referral code
        self.referrer = User.objects.create_user(
            username="referrer", email="referrer@example.com", password="testpass123"
        )
        self.referrer.profile.referral_code = "TEST123"
        self.referrer.profile.save()

    def test_signup_with_referral_code(self):
        """Test that signup works with and without a referral code"""
        # Test without referral code.
        data = {
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
            "is_profile_public": False,  # New required field
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created without referral.
        new_user = User.objects.get(email="newuser@example.com")
        self.assertIsNone(new_user.profile.referred_by)

        # Test with invalid referral code.
        data = {
            "email": "anotheruser@example.com",
            "first_name": "Another",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "referral_code": "INVALID",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
            "is_profile_public": False,  # Include the field here as well
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Invalid referral code", str(response.context["form"].errors["referral_code"]))

        # Test with valid referral code.
        data["referral_code"] = "TEST123"
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created and referral was handled.
        another_user = User.objects.get(email="anotheruser@example.com")
        self.assertEqual(another_user.profile.referred_by, self.referrer.profile)

    def test_signup_form_validation(self):
        """Test form validation for invalid submissions"""
        # Test empty form
        response = self.client.post(self.signup_url, {})
        self.assertEqual(response.status_code, 200)
        self.assertIn("This field is required.", str(response.context["form"].errors["email"]))

        # Test invalid email
        data = {
            "email": "invalid-email",
            "first_name": "Test",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "referral_code": "TEST123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Enter a valid email address.",
            str(response.context["form"].errors["email"]),
        )

    @patch("allauth.account.signals.email_confirmed")
    @patch("allauth.account.signals.user_signed_up")
    def test_successful_signup_as_student(self, mock_signed_up, mock_email_confirmed):
        """Test successful signup as a student"""
        data = {
            "email": "student@example.com",
            "first_name": "Student",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "referral_code": "TEST123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
            "is_profile_public": False,
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created
        self.assertEqual(User.objects.count(), 2)  # Including the referrer
        user = User.objects.get(email="student@example.com")
        self.assertEqual(user.email, "student@example.com")
        self.assertFalse(user.profile.is_teacher)
        self.assertEqual(user.profile.referred_by, self.referrer.profile)

        # Verify email address
        email = EmailAddress.objects.get(user=user, email=user.email)
        email.verified = True
        email.save()
        mock_email_confirmed.send()
        mock_signed_up.send(sender=user.__class__, request=None, user=user)

    @patch("allauth.account.signals.email_confirmed")
    @patch("allauth.account.signals.user_signed_up")
    def test_successful_signup_as_teacher(self, mock_signed_up, mock_email_confirmed):
        """Test successful signup as a teacher"""
        data = {
            "email": "teacher@example.com",
            "first_name": "Teacher",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "is_teacher": "on",
            "referral_code": "TEST123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
            "is_profile_public": True,  # New required field
        }
        response = self.client.post(self.signup_url, data)
        self.assertEqual(response.status_code, 302)  # Should redirect after successful signup

        # Verify user was created
        self.assertEqual(User.objects.count(), 2)  # Including the referrer
        user = User.objects.get(email="teacher@example.com")
        self.assertEqual(user.email, "teacher@example.com")
        self.assertTrue(user.profile.is_teacher)
        self.assertEqual(user.profile.referred_by, self.referrer.profile)

        # Verify email address
        email = EmailAddress.objects.get(user=user, email=user.email)
        self.assertFalse(email.verified)  # Should be unverified initially

        # Verify response redirects to confirm-email URL
        self.assertTrue("/accounts/confirm-email/" in response.url)

        # Simulate email verification
        email.verified = True
        email.save()
        mock_email_confirmed.send()
        mock_signed_up.send(sender=user.__class__, request=None, user=user)

    def test_duplicate_email_signup(self):
        """Test signup with an email that's already in use"""
        # First create a user
        # We don't use the variable directly but need to create this user for the test
        User.objects.create_user(username="existinguser", email="duplicate@example.com", password="testpass123")

        # Now try to sign up with the same email
        data = {
            "email": "duplicate@example.com",  # Same email as existing user
            "first_name": "Another",
            "last_name": "User",
            "password1": "newpass123",
            "password2": "newpass123",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        response = self.client.post(self.signup_url, data)

        # Should stay on the signup page with an error
        self.assertEqual(response.status_code, 200)

        # Verify the vague error message (not explicitly saying email exists)
        form_errors = str(response.context["form"].errors.get("email", ""))
        self.assertIn("There was a problem with your signup", form_errors)
        self.assertNotIn("already in use", form_errors)
        self.assertNotIn("already exists", form_errors)
