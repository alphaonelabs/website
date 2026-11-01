from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.text import slugify

from web.models import Course, Enrollment, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class FreeCourseEnrollmentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock stripe module
        cls.stripe_patcher = patch("web.views.stripe")
        cls.mock_stripe = cls.stripe_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.stripe_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        # Create a subject for the course
        self.subject = Subject.objects.create(
            name="Free Courses", slug="free-courses", description="Free courses", icon="fas fa-gift"
        )

        # Create a teacher
        self.teacher = User.objects.create_user(
            username="freeteacher", password="teacherpass", email="freeteacher@example.com"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a free course (price=0)
        self.free_course = Course.objects.create(
            title="Free Test Course",
            slug=slugify("Free Test Course"),
            teacher=self.teacher,
            description="A free test course",
            learning_objectives="Learn free stuff",
            prerequisites="None",
            price=0.00,  # Free course
            allow_individual_sessions=False,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

        # Create a paid course for comparison
        self.paid_course = Course.objects.create(
            title="Paid Test Course",
            slug=slugify("Paid Test Course"),
            teacher=self.teacher,
            description="A paid test course",
            learning_objectives="Learn paid stuff",
            prerequisites="None",
            price=9.99,  # Paid course
            allow_individual_sessions=False,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )

        # Create a student
        self.student = User.objects.create_user(
            username="freestudent", password="studentpass", email="freestudent@example.com"
        )

    def test_enroll_free_course(self):
        """Test that enrolling in a free course bypasses payment and creates an approved enrollment."""
        # Reset mock to clear any previous calls
        self.mock_stripe.reset_mock()

        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Enroll in the free course
        url = reverse("enroll_course", args=[self.free_course.slug])
        response = self.client.get(url)

        # Should redirect to course detail page
        self.assertRedirects(response, reverse("course_detail", args=[self.free_course.slug]))

        # Check that an approved enrollment was created
        enrollment = Enrollment.objects.get(student=self.student, course=self.free_course)
        self.assertEqual(enrollment.status, "approved")

    def test_enroll_paid_course(self):
        """Test that enrolling in a paid course creates a pending enrollment."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Enroll in the paid course
        url = reverse("enroll_course", args=[self.paid_course.slug])
        response = self.client.get(url)

        # Should redirect to course detail page
        self.assertRedirects(response, reverse("course_detail", args=[self.paid_course.slug]))

        # Check that a pending enrollment was created
        enrollment = Enrollment.objects.get(student=self.student, course=self.paid_course)
        self.assertEqual(enrollment.status, "pending")

    def test_create_payment_intent_free_course(self):
        """Test that create_payment_intent approves enrollment for free courses without creating a payment intent."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Enroll in the free course (creates a pending enrollment)
        enrollment = Enrollment.objects.create(student=self.student, course=self.free_course, status="pending")

        # Call create_payment_intent endpoint
        url = reverse("create_payment_intent", args=[self.free_course.slug])
        response = self.client.get(url)

        # Check response indicates free course
        self.assertEqual(response.status_code, 200)
        self.assertIn("free_course", response.json())
        self.assertTrue(response.json()["free_course"])

        # Verify enrollment was approved
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, "approved")

        # Verify stripe.PaymentIntent.create was not called
        self.mock_stripe.PaymentIntent.create.assert_not_called()

    def test_create_payment_intent_paid_course(self):
        """Test that create_payment_intent creates a payment intent for paid courses."""
        # Set up mock payment intent
        mock_intent = type(
            "obj",
            (object,),
            {
                "client_secret": "test_secret",
            },
        )
        self.mock_stripe.PaymentIntent.create.return_value = mock_intent

        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Enroll in the paid course (creates a pending enrollment)
        enrollment = Enrollment.objects.create(student=self.student, course=self.paid_course, status="pending")

        # Call create_payment_intent endpoint
        url = reverse("create_payment_intent", args=[self.paid_course.slug])
        response = self.client.get(url)

        # Check response contains client secret
        self.assertEqual(response.status_code, 200)
        self.assertIn("clientSecret", response.json())

        # Verify enrollment still pending
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, "pending")

        # Verify stripe.PaymentIntent.create was called
        self.mock_stripe.PaymentIntent.create.assert_called_once()
