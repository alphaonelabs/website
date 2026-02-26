from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import ProgressTracker


class ProgressTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", password="testpassword", email="testuser@example.com"
        )
        self.client.login(username="testuser", password="testpassword")
        self.tracker = ProgressTracker.objects.create(
            user=self.user,
            title="Test Tracker",
            description="Testing progress",
            current_value=25,
            target_value=100,
            color="blue-600",
            public=True,
        )

    def test_tracker_list(self):
        response = self.client.get(reverse("tracker_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")

    def test_create_tracker(self):
        """response = self.client.post(reverse('create_tracker'), {
            'title': 'New Tracker',
            'description': 'New description',
            'current_value': 10,
            'target_value': 50,
            'color': 'green-600',
            'public': True
        })"""
        self.assertEqual(ProgressTracker.objects.count(), 2)
        new_tracker = ProgressTracker.objects.get(title="New Tracker")
        self.assertEqual(new_tracker.current_value, 10)
        self.assertEqual(new_tracker.percentage, 20)

    def test_update_progress(self):
        response = self.client.post(
            reverse("update_progress", args=[self.tracker.id]),
            {"current_value": 50},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.tracker.refresh_from_db()
        self.assertEqual(self.tracker.current_value, 50)
        self.assertEqual(self.tracker.percentage, 50)

    def test_embed_tracker(self):
        response = self.client.get(reverse("embed_tracker", args=[self.tracker.embed_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")
        self.assertContains(response, "25%")


from web.models import Notification


class NotificationCenterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="notifuser", password="testpassword", email="notifuser@example.com"
        )
        self.client.login(username="notifuser", password="testpassword")
        self.notification = Notification.objects.create(
            user=self.user,
            title="Test Notification",
            message="This is a test notification.",
            notification_type="info",
            read=False,
        )

    def test_notification_center_view(self):
        response = self.client.get(reverse("notification_center"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Notification")

    def test_notification_center_filter_unread(self):
        Notification.objects.create(
            user=self.user,
            title="Read Notification",
            message="Already read.",
            notification_type="success",
            read=True,
        )
        response = self.client.get(reverse("notification_center") + "?filter=unread")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Notification")
        self.assertNotContains(response, "Read Notification")

    def test_notification_center_filter_read(self):
        read_notif = Notification.objects.create(
            user=self.user,
            title="Read Notification",
            message="Already read.",
            notification_type="success",
            read=True,
        )
        response = self.client.get(reverse("notification_center") + "?filter=read")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, read_notif.title)
        self.assertNotContains(response, "Test Notification")

    def test_mark_notification_read(self):
        response = self.client.post(reverse("mark_notification_read", args=[self.notification.id]))
        self.assertEqual(response.status_code, 200)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.read)

    def test_mark_all_notifications_read(self):
        Notification.objects.create(
            user=self.user,
            title="Another Unread",
            message="Also unread.",
            notification_type="warning",
            read=False,
        )
        response = self.client.post(reverse("mark_all_notifications_read"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Notification.objects.filter(user=self.user, read=False).count(), 0)

    def test_delete_notification(self):
        response = self.client.post(reverse("delete_notification", args=[self.notification.id]))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Notification.objects.filter(id=self.notification.id).exists())

    def test_cannot_access_other_users_notification(self):
        other_user = User.objects.create_user(
            username="otheruser", password="testpassword", email="other@example.com"
        )
        other_notif = Notification.objects.create(
            user=other_user,
            title="Private Notification",
            message="Not yours.",
            notification_type="info",
        )
        response = self.client.post(reverse("mark_notification_read", args=[other_notif.id]))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_redirect(self):
        self.client.logout()
        response = self.client.get(reverse("notification_center"))
        self.assertEqual(response.status_code, 302)

    def test_unread_count_context_processor(self):
        response = self.client.get(reverse("notification_center"))
        self.assertEqual(response.context["unread_count"], 1)
