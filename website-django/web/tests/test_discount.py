from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from web.models import Course, Discount, Subject

User = get_user_model()


class DiscountReferrerTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user and log in.
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client.login(username="testuser", password="testpass")

        # Create a dummy subject.
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")

        # Create a test course.
        self.course = Course.objects.create(
            title="English",
            slug="english",
            teacher=self.user,
            description="Test course description",
            learning_objectives="Test objectives",
            prerequisites="None",
            price=100.00,
            allow_individual_sessions=False,
            invite_only=False,
            status="published",
            max_students=10,
            subject=self.subject,
            level="beginner",
            tags="",
            is_featured=False,
        )

    def test_missing_course_id(self):
        """GET request without course_id should return 400."""
        url = reverse("apply_discount_via_referrer")
        response = self.client.get(url, HTTP_REFERER="https://twitter.com")
        self.assertEqual(response.status_code, 400)

    def test_invalid_referrer(self):
        """
        Test that when the referrer header does NOT indicate Twitter (or t.co),
        the view does not create a discount and redirects to the profile.
        """
        url = reverse("apply_discount_via_referrer") + f"?course_id={self.course.id}"
        response = self.client.get(url, HTTP_REFERER="https://example.com")
        # Expect a redirect to profile.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profile"))

        # Ensure no discount record was created.
        discount = Discount.objects.filter(user=self.user, course=self.course, used=False).first()
        self.assertIsNone(discount)

    def test_valid_referrer_creates_discount(self):
        """
        When a valid referrer (from Twitter) is provided, a discount record should be created,
        and the view should redirect to the profile.
        """
        url = reverse("apply_discount_via_referrer") + f"?course_id={self.course.id}"
        response = self.client.get(url, HTTP_REFERER="https://twitter.com")
        # Expect a redirect to profile.
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("profile"))

        # Discount record should exist.
        discount = Discount.objects.filter(user=self.user, course=self.course, used=False).first()
        self.assertIsNotNone(discount)

    def test_discount_appears_in_profile(self):
        """
        After triggering the discount view with a valid referrer,
        the profile page should render the discount code.
        """
        # Trigger discount creation.
        discount_url = reverse("apply_discount_via_referrer") + f"?course_id={self.course.id}"
        self.client.get(discount_url, HTTP_REFERER="https://twitter.com")

        # Now get the profile page.
        profile_url = reverse("profile")
        response = self.client.get(profile_url)

        # Check that the discount codes section is rendered.
        self.assertContains(response, "Your Discount Codes")
        # Also, verify that the created discount code appears.
        discount = Discount.objects.filter(user=self.user, course=self.course, used=False).first()
        self.assertIsNotNone(discount)
        self.assertContains(response, discount.code)
