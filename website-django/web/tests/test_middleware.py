from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.models import Challenge, Course, Subject, WebRequest


class WebRequestMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Create test subject
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject", description="Test Description")

        # Create test course
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            description="Test Description",
            learning_objectives="Test Objectives",
            teacher=self.user,
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
            status="published",
            is_featured=True,
        )

        # Create a test challenge for the homepage
        self.challenge = Challenge.objects.create(
            title="Test Challenge",
            description="Test Description",
            week_number=1,
            start_date=timezone.now() - timezone.timedelta(days=1),
            end_date=timezone.now() + timezone.timedelta(days=6),
        )

    def test_web_request_tracking_course_detail(self):
        """Test that course detail page views are tracked correctly"""
        # Visit course detail page
        course_url = reverse("course_detail", kwargs={"slug": self.course.slug})
        response = self.client.get(course_url, HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Check that WebRequest was created
        web_request = WebRequest.objects.first()
        self.assertIsNotNone(web_request)
        self.assertEqual(web_request.path, course_url)
        self.assertEqual(web_request.count, 1)
        self.assertEqual(web_request.course, self.course)
        self.assertEqual(web_request.agent, "Test Agent")
        self.assertEqual(web_request.ip_address, "1.2.3.4")

        # Visit the same page again with same client info
        response = self.client.get(course_url, HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Check that count was incremented
        web_request.refresh_from_db()
        self.assertEqual(web_request.count, 2)

        # Total WebRequest objects should still be 1
        self.assertEqual(WebRequest.objects.count(), 1)

    def test_web_request_tracking_different_clients(self):
        """Test that different clients create separate WebRequest entries"""
        course_url = reverse("course_detail", kwargs={"slug": self.course.slug})

        # First client visit
        response = self.client.get(course_url, HTTP_USER_AGENT="Client 1", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Second client visit with different IP
        response = self.client.get(course_url, HTTP_USER_AGENT="Client 1", REMOTE_ADDR="5.6.7.8")
        self.assertEqual(response.status_code, 200)

        # Third client visit with different agent but same IP as first
        response = self.client.get(course_url, HTTP_USER_AGENT="Client 2", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Should have three separate WebRequest entries
        self.assertEqual(WebRequest.objects.count(), 3)

        # Check that counts are correct
        requests = WebRequest.objects.all()
        for request in requests:
            self.assertEqual(request.count, 1)

    def test_web_request_tracking_non_course_pages(self):
        """Test that non-course pages are also tracked"""
        # Visit homepage
        home_url = reverse("index")
        response = self.client.get(home_url, HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Check that WebRequest was created
        web_request = WebRequest.objects.first()
        self.assertIsNotNone(web_request)
        self.assertEqual(web_request.path, home_url)
        self.assertEqual(web_request.count, 1)
        self.assertIsNone(web_request.course)  # Course should be None for non-course pages
        self.assertEqual(web_request.ip_address, "1.2.3.4")

    def test_web_request_tracking_authenticated_user(self):
        """Test that authenticated users are tracked correctly"""
        # Login user
        self.client.login(username="testuser", password="testpass123")

        # Visit course detail page
        course_url = reverse("course_detail", kwargs={"slug": self.course.slug})
        response = self.client.get(course_url, HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 200)

        # Check that WebRequest was created with user info
        web_request = WebRequest.objects.first()
        self.assertIsNotNone(web_request)
        self.assertEqual(web_request.user, "testuser")
        self.assertEqual(web_request.ip_address, "1.2.3.4")

    def test_web_request_tracking_with_referer(self):
        """Test that referer information is tracked correctly"""
        course_url = reverse("course_detail", kwargs={"slug": self.course.slug})
        referer_url = "https://example.com/some-page"

        # Visit page with referer
        response = self.client.get(
            course_url, HTTP_USER_AGENT="Test Agent", HTTP_REFERER=referer_url, REMOTE_ADDR="1.2.3.4"
        )
        self.assertEqual(response.status_code, 200)

        # Check that WebRequest was created with referer info
        web_request = WebRequest.objects.first()
        self.assertIsNotNone(web_request)
        self.assertEqual(web_request.referer, referer_url)
        self.assertEqual(web_request.ip_address, "1.2.3.4")

    @override_settings(
        STATIC_URL="/static/",
        DEBUG=False,
    )
    def test_static_files_not_tracked(self):
        """Test that static file requests are not tracked"""
        # Request a path that starts with STATIC_URL
        self.client.get("/static/images/non-existent-file.png", HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        # The actual response status code doesn't matter for this test
        # We only care that no WebRequest was created

        # No WebRequest should be created for static file paths
        self.assertEqual(WebRequest.objects.count(), 0)

    @override_settings(
        DEBUG=True,
        MIDDLEWARE=[
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "web.middleware.WebRequestMiddleware",
        ],
    )
    def test_invalid_course_slug(self):
        """Test handling of requests with invalid course slugs"""
        # Visit course detail with invalid slug
        course_url = reverse("course_detail", kwargs={"slug": "invalid-slug"})

        # Try the request without GlobalExceptionMiddleware
        response = self.client.get(course_url, HTTP_USER_AGENT="Test Agent", REMOTE_ADDR="1.2.3.4")
        self.assertEqual(response.status_code, 404)

        # WebRequest should still be created but without course association
        web_request = WebRequest.objects.first()
        if web_request:
            print(
                "WebRequest details:",
                {
                    "path": web_request.path,
                    "course": web_request.course,
                    "ip_address": web_request.ip_address,
                    "count": web_request.count,
                    "user": web_request.user,
                    "agent": web_request.agent,
                    "referer": web_request.referer,
                },
            )
        self.assertIsNotNone(web_request)
        self.assertEqual(web_request.path, course_url)
        self.assertIsNone(web_request.course)
        self.assertEqual(web_request.ip_address, "1.2.3.4")
