from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.text import slugify

from web.models import Cart, CartItem, Course, Enrollment, Subject


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class FreeCartCheckoutTest(TestCase):
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

        # Create free courses
        self.free_course1 = Course.objects.create(
            title="Free Test Course 1",
            slug=slugify("Free Test Course 1"),
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

        self.free_course2 = Course.objects.create(
            title="Free Test Course 2",
            slug=slugify("Free Test Course 2"),
            teacher=self.teacher,
            description="Another free test course",
            learning_objectives="Learn more free stuff",
            prerequisites="None",
            price=0.00,  # Free course
            allow_individual_sessions=False,
            max_students=50,
            subject=self.subject,
            level="intermediate",
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

    def test_create_payment_intent_free_cart(self):
        """Test that create_cart_payment_intent returns free_cart flag for cart with only free courses."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Add free courses to cart
        cart = Cart.objects.create(user=self.student)
        CartItem.objects.create(cart=cart, course=self.free_course1)
        CartItem.objects.create(cart=cart, course=self.free_course2)

        # Verify cart total is 0
        self.assertEqual(cart.total, 0)

        # Call create_cart_payment_intent endpoint
        url = reverse("create_cart_payment_intent")
        response = self.client.get(url)

        # Check response indicates free cart
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("free_cart", data)
        self.assertTrue(data["free_cart"])

        # Verify stripe.PaymentIntent.create was not called
        self.mock_stripe.PaymentIntent.create.assert_not_called()

    def test_create_payment_intent_mixed_cart(self):
        """Test that create_cart_payment_intent creates payment intent for cart with paid items."""
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

        # Add free and paid courses to cart
        cart = Cart.objects.create(user=self.student)
        CartItem.objects.create(cart=cart, course=self.free_course1)
        CartItem.objects.create(cart=cart, course=self.paid_course)

        # Verify cart total is > 0
        self.assertGreater(cart.total, 0)

        # Call create_cart_payment_intent endpoint
        url = reverse("create_cart_payment_intent")
        response = self.client.get(url)

        # Check response contains client secret
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("clientSecret", data)

        # Verify stripe.PaymentIntent.create was called
        self.mock_stripe.PaymentIntent.create.assert_called_once()

    def test_free_cart_checkout(self):
        """Test that free_cart_checkout creates enrollments without payment for free courses."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Add free courses to cart
        cart = Cart.objects.create(user=self.student)
        CartItem.objects.create(cart=cart, course=self.free_course1)
        CartItem.objects.create(cart=cart, course=self.free_course2)

        # Call free_cart_checkout endpoint
        url = reverse("free_cart_checkout")
        response = self.client.post(url, follow=True)

        # Check response is successful (redirects to receipt page)
        self.assertEqual(response.status_code, 200)

        # Verify enrollments were created
        enrollment1 = Enrollment.objects.filter(student=self.student, course=self.free_course1).first()
        enrollment2 = Enrollment.objects.filter(student=self.student, course=self.free_course2).first()

        self.assertIsNotNone(enrollment1)
        self.assertIsNotNone(enrollment2)
        self.assertEqual(enrollment1.status, "approved")
        self.assertEqual(enrollment2.status, "approved")
        self.assertEqual(enrollment1.payment_intent_id, "")
        self.assertEqual(enrollment2.payment_intent_id, "")

        # Verify cart was cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 0)

    def test_free_cart_checkout_with_paid_items_fails(self):
        """Test that free_cart_checkout rejects cart with paid items."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Add paid course to cart
        cart = Cart.objects.create(user=self.student)
        CartItem.objects.create(cart=cart, course=self.paid_course)

        # Call free_cart_checkout endpoint
        url = reverse("free_cart_checkout")
        response = self.client.post(url, follow=True)

        # Check that request was redirected to cart_view
        self.assertRedirects(response, reverse("cart_view"))

        # Verify no enrollment was created
        enrollment = Enrollment.objects.filter(student=self.student, course=self.paid_course).first()
        self.assertIsNone(enrollment)

        # Verify cart was not cleared
        cart.refresh_from_db()
        self.assertEqual(cart.items.count(), 1)

    def test_free_cart_checkout_requires_authentication(self):
        """Test that free_cart_checkout requires user to be logged in."""
        # Create a cart without logging in
        cart = Cart.objects.create(session_key="test_session_key")
        CartItem.objects.create(cart=cart, course=self.free_course1)

        # Call free_cart_checkout endpoint without login
        url = reverse("free_cart_checkout")
        response = self.client.post(url)

        # Check that request was redirected to login page
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_free_cart_checkout_empty_cart(self):
        """Test that free_cart_checkout handles empty cart gracefully."""
        # Student logs in
        self.client.login(username="freestudent", password="studentpass")

        # Create empty cart
        Cart.objects.create(user=self.student)

        # Call free_cart_checkout endpoint
        url = reverse("free_cart_checkout")
        response = self.client.post(url, follow=True)

        # Check that request was redirected to cart_view
        self.assertRedirects(response, reverse("cart_view"))
