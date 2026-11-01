from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from web.models import Challenge, ChallengeSubmission, Points

"""
To run this test run this command:  python manage.py test web.tests.test_leaderboard.
Then login with this credentials:
    Email: student1@example.com
    Password: testpass123
OR
    Email: student2@example.com
    Password: testpass123
"""


class LeaderboardTestCase(TestCase):
    def setUp(self):
        # This runs before each test
        self.client = Client()

        # Create test users within the test database
        self.test_user = User.objects.create_user(
            username="student1", email="student1@example.com", password="testpass123"
        )

        # Create a second user for testing
        self.test_user2 = User.objects.create_user(
            username="student2", email="student2@example.com", password="testpass123"
        )

        # Create test challenges
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            description="Test Description",
            week_number=1,
            start_date="2025-03-01",
            end_date="2025-03-07",
        )

        # Create a submission and points
        self.submission = ChallengeSubmission.objects.create(
            user=self.test_user, challenge=self.challenge, submission_text="Test submission", points_awarded=10
        )

        # Add some extra points
        Points.objects.create(user=self.test_user, amount=15, reason="Test points", point_type="regular")

    def test_with_force_login(self):
        # Use the user we created in setUp
        self.client.force_login(self.test_user)

        # Add follow=True to follow the redirect
        response = self.client.get("/profile/", follow=True)
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_access(self):
        # Log in the user
        self.client.force_login(self.test_user)

        # Try common URL names for leaderboard
        try:
            leaderboard_url = reverse("leaderboard_main")  # Try common URL names
        except NoReverseMatch:
            leaderboard_url = "/en/leaderboards/"  # Note: plural form

        # Add follow=True to follow redirects
        response = self.client.get(leaderboard_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # Check for leaderboard content
        self.assertContains(response, self.test_user.username)
