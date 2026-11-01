from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from web.models import LearningStreak

User = get_user_model()


class LearningStreakEdgeCaseTests(TestCase):
    def setUp(self):
        # Create a test user and a corresponding LearningStreak record.
        self.user = User.objects.create_user(username="edgeuser", password="pass")
        self.streak = LearningStreak.objects.create(user=self.user)

    def test_first_time_engagement(self):
        """
        If the user has no previous engagement, update_streak should set
        current_streak to 1, longest_streak to 1, and last_engagement to today.
        """
        self.assertIsNone(self.streak.last_engagement)
        self.streak.update_streak()
        today = timezone.now().date()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.longest_streak, 1)
        self.assertEqual(self.streak.last_engagement, today)

    def test_consecutive_engagement(self):
        """
        If the last engagement was exactly one day ago, the streak should increment by 1.
        """
        yesterday = timezone.now().date() - timedelta(days=1)
        self.streak.last_engagement = yesterday
        self.streak.current_streak = 1
        self.streak.longest_streak = 1
        self.streak.save()
        self.streak.update_streak()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 2)
        self.assertEqual(self.streak.longest_streak, 2)

    def test_non_consecutive_engagement(self):
        """
        If the gap between the last engagement and today is more than one day,
        update_streak should reset current_streak to 1. The longest_streak remains unchanged.
        """
        two_days_ago = timezone.now().date() - timedelta(days=2)
        self.streak.last_engagement = two_days_ago
        self.streak.current_streak = 3
        self.streak.longest_streak = 3
        self.streak.save()
        self.streak.update_streak()
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.longest_streak, 3)

    def test_future_engagement(self):
        """
        If the last engagement is set in the future, update_streak should treat it as an invalid date.
        The expected behavior is to reset current_streak to 1 and update last_engagement to today.
        The longest_streak remains unchanged if the new current_streak doesn't exceed it.
        """
        tomorrow = timezone.now().date() + timedelta(days=1)
        self.streak.last_engagement = tomorrow
        self.streak.current_streak = 5
        self.streak.longest_streak = 5
        self.streak.save()
        self.streak.update_streak()
        self.streak.refresh_from_db()
        today = timezone.now().date()
        self.assertEqual(self.streak.current_streak, 1)
        self.assertEqual(self.streak.longest_streak, 5)
        self.assertEqual(self.streak.last_engagement, today)
