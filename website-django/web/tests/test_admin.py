import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

User = get_user_model()

TEMP_DIR = tempfile.mkdtemp()


@override_settings(
    DEBUG=True,
    SLACK_WEBHOOK_URL=None,
    STATIC_ROOT=TEMP_DIR,
)
class AdminTests(TestCase):
    def setUp(self):
        # Create superuser for admin access
        self.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )
        self.client = Client()
        success = self.client.login(username="admin", password="adminpass123")
        self.assertTrue(success, "Login failed")

    def test_create_user_through_admin(self):
        """Test that a user can be created through the admin interface"""
        initial_user_count = User.objects.count()
        self.assertEqual(initial_user_count, 1)  # Just the admin user

        # Create the user with initial data
        initial_data = {
            "username": "testuser",
            "password1": "testpass123",
            "password2": "testpass123",
            "email": "testuser@example.com",
            "first_name": "Test",
            "last_name": "User",
            "is_staff": "0",
            "is_active": "1",
            "is_superuser": "0",
            "date_joined_0": "2024-01-01",
            "date_joined_1": "00:00:00",
            "initial-email": "testuser@example.com",
            "profile-TOTAL_FORMS": "1",
            "profile-INITIAL_FORMS": "0",
            "profile-MIN_NUM_FORMS": "0",
            "profile-MAX_NUM_FORMS": "1",
            "profile-0-id": "",
            "profile-0-user": "",
            "profile-0-bio": "Test bio",
            "profile-0-expertise": "Test expertise",
            "profile-0-is_teacher": "1",
            "profile-0-referral_earnings": "0",
            "profile-0-commission_rate": "10.0",
            "profile-0-referred_by": "",
            # Email address inline formset
            "emailaddress_set-TOTAL_FORMS": "1",
            "emailaddress_set-INITIAL_FORMS": "0",
            "emailaddress_set-MIN_NUM_FORMS": "0",
            "emailaddress_set-MAX_NUM_FORMS": "1000",
            "emailaddress_set-0-email": "testuser@example.com",
            "emailaddress_set-0-verified": "1",
            "emailaddress_set-0-primary": "1",
            "emailaddress_set-0-id": "",
            "emailaddress_set-0-user": "",
            "_save": "Save",
        }

        # Build the admin URL using the settings
        admin_add_user_url = f"/en/{settings.ADMIN_URL}/auth/user/add/"
        response = self.client.post(admin_add_user_url, initial_data, follow=True)

        # Check if we got redirected to the user change page
        self.assertTrue(
            any(redirect[0].endswith("/change/") for redirect in response.redirect_chain),
            "Expected redirect to change page not found",
        )

        # Verify the user was created
        try:
            user = User.objects.get(username="testuser")
        except User.DoesNotExist:
            all_users = User.objects.all()
            user_details = [f"{u.username} ({u.email})" for u in all_users]
            self.fail(f"User was not created. All users: {', '.join(user_details)}")

        self.assertEqual(User.objects.count(), 2)  # Admin + new user

        # Verify the profile was created
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.bio, "Test bio")
        self.assertEqual(user.profile.expertise, "Test expertise")
        self.assertTrue(user.profile.is_teacher)

        # Verify email was set
        self.assertEqual(user.email, "testuser@example.com")
        email_exists = user.emailaddress_set.filter(email="testuser@example.com", verified=True, primary=True).exists()
        self.assertTrue(email_exists)
