from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import ProgressTracker


class ProgressTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
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


from web.models import Course, CourseBookmark, Subject


class CourseBookmarkTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="bookmarkuser", password="testpass123", email="bookmarkuser@test.com"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", password="testpass123", email="otheruser@test.com"
        )
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")
        self.teacher = User.objects.create_user(
            username="teacher", password="testpass123", email="teacher@test.com"
        )
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.teacher,
            subject=self.subject,
            description="A test course",
            price=0,
            max_students=30,
        )
        self.client.login(username="bookmarkuser", password="testpass123")

    def test_toggle_bookmark_on(self):
        response = self.client.post(reverse("toggle_bookmark", args=["test-course"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["bookmarked"])
        self.assertTrue(CourseBookmark.objects.filter(user=self.user, course=self.course).exists())

    def test_toggle_bookmark_off(self):
        CourseBookmark.objects.create(user=self.user, course=self.course)
        response = self.client.post(reverse("toggle_bookmark", args=["test-course"]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["bookmarked"])
        self.assertFalse(CourseBookmark.objects.filter(user=self.user, course=self.course).exists())

    def test_bookmarks_list_page(self):
        CourseBookmark.objects.create(user=self.user, course=self.course)
        response = self.client.get(reverse("my_bookmarks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")

    def test_bookmarks_list_empty(self):
        response = self.client.get(reverse("my_bookmarks"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No bookmarks yet")

    def test_unauthenticated_toggle_redirects(self):
        self.client.logout()
        response = self.client.post(reverse("toggle_bookmark", args=["test-course"]))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_bookmarks_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("my_bookmarks"))
        self.assertEqual(response.status_code, 302)

    def test_bookmark_shows_on_course_detail(self):
        CourseBookmark.objects.create(user=self.user, course=self.course)
        response = self.client.get(reverse("course_detail", args=["test-course"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="bookmark-icon-filled"')

    def test_no_bookmark_shows_empty_heart(self):
        response = self.client.get(reverse("course_detail", args=["test-course"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="bookmark-icon-outline"')
