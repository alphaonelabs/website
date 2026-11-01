from decimal import Decimal
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from web.forms import LearnForm, TeachForm
from web.models import Course, Enrollment, Profile, Session, SessionAttendance, Subject
from web.utils import get_or_create_cart
from web.views import send_welcome_email


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class BaseViewTest(TestCase):
    def setUp(self):
        # Debug statement

        self.client = Client()

        # Create teacher user and profile
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
        )
        self.teacher_profile, created_teacher_profile = Profile.objects.get_or_create(
            user=self.teacher,
            defaults={"is_teacher": True},
        )

        # Create student user and profile
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
        )
        self.student_profile, created_student_profile = Profile.objects.get_or_create(
            user=self.student,
            defaults={"is_teacher": False},
        )

        # Create test subject
        self.subject = Subject.objects.create(
            name="Programming2",
            slug="programming2",
            description="Programming courses",
            icon="fas fa-code",
        )

        # Create test course
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            learning_objectives="Test Objectives",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
        )


@override_settings(
    ACCOUNT_EMAIL_VERIFICATION="mandatory",
    ACCOUNT_EMAIL_REQUIRED=True,
    ACCOUNT_USERNAME_REQUIRED=True,
    ACCOUNT_AUTHENTICATION_METHOD="email",
    ACCOUNT_RATE_LIMITS={
        "login_attempt": "5/5m",
        "login_failed": "3/5m",
        "signup": "5/h",
        "send_email": "5/5m",
        "change_email": "3/h",
    },
)
class AuthenticationTests(TestCase):
    def setUp(self):
        # Debug statement

        self.client = Client()
        self.username = "testuser"
        self.email = "test@example.com"
        self.password = "testpass123"

        # Create user with username (required) but login will use email
        self.user = User.objects.create_user(
            username=self.username,
            email=self.email,
            password=self.password,
        )

        # Verify email for allauth
        EmailAddress.objects.create(
            user=self.user,
            email=self.email,
            primary=True,
            verified=True,
        )
        self.login_url = reverse("account_login")

    def test_successful_login_with_email(self):
        """Test that a user can successfully login with email and password"""

        self.client.logout()

        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

        # Attempt login
        login_data = {"login": self.email, "password": self.password}
        response = self.client.post(self.login_url, login_data, follow=True)

        # Check that login was successful
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)
        self.assertEqual(response.context["user"].email, self.email)


@override_settings(
    STRIPE_SECRET_KEY="dummy_key",
    STRIPE_PUBLIC_KEY="dummy_pub_key",
    GOOGLE_CALENDAR_ENABLED=False,
    SLACK_ENABLED=False,
    SLACK_WEBHOOK_URL="https://dummy-slack-url.com",
    GOOGLE_CREDENTIALS_PATH="dummy_path",
)
class CartCheckoutTest(BaseViewTest):
    def setUp(self):
        # First call parent setUp
        super().setUp()

        # Allow individual sessions for the course
        self.course.allow_individual_sessions = True
        self.course.save()

        # Create test session
        start = timezone.now() + timezone.timedelta(days=1)
        end = start + timezone.timedelta(hours=1)
        self.session = Session.objects.create(
            course=self.course,
            title="Test Session",
            description="Test Session Description",
            start_time=start,
            end_time=end,
            price=Decimal("29.99"),
        )
        self.cart_url = reverse("cart_view")
        self.add_course_url = reverse("add_course_to_cart", args=[self.course.id])
        self.add_session_url = reverse("add_session_to_cart", args=[self.session.id])

    @patch("web.views.send_welcome_email")
    @patch("stripe.PaymentIntent.retrieve")
    def test_guest_cart_checkout_flow(self, mock_retrieve, mock_welcome_email):
        """Test that a guest user can add items to cart and checkout"""
        # Mock the payment intent
        mock_payment_intent = type("PaymentIntent", (), {"status": "succeeded", "receipt_email": "test@example.com"})
        mock_retrieve.return_value = mock_payment_intent

        # Add course to cart
        response = self.client.post(self.add_course_url)
        self.assertEqual(response.status_code, 302)

        # Add session to cart
        response = self.client.post(self.add_session_url)
        self.assertEqual(response.status_code, 302)

        # Check cart contents
        response = self.client.get(self.cart_url)
        cart = get_or_create_cart(response.wsgi_request)
        self.assertEqual(cart.items.count(), 2)
        self.assertTrue(cart.items.filter(course=self.course).exists())
        self.assertTrue(cart.items.filter(session=self.session).exists())

        # Process checkout
        response = self.client.get(reverse("checkout_success") + "?payment_intent=pi_test_123")
        self.assertEqual(response.status_code, 200)

        # Verify receipt page
        self.assertTemplateUsed(response, "cart/receipt.html")
        self.assertEqual(response.context["payment_intent_id"], "pi_test_123")
        self.assertEqual(response.context["user"].email, "test@example.com")
        self.assertEqual(len(response.context["enrollments"]), 1)
        self.assertEqual(len(response.context["session_enrollments"]), 1)
        expected_total = Decimal("129.98")  # 99.99 for course + 29.99 for session
        self.assertEqual(response.context["total"], expected_total)

    def test_send_welcome_email(self):
        """Test that welcome email is sent correctly to new users"""
        # Test case 1: Normal user with email
        user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        send_welcome_email(user)

        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Verify email properties
        self.assertEqual(email.subject, "Welcome to Your New Learning Account")
        self.assertEqual(email.to, ["test@example.com"])

        # Get reset URL
        reset_url = reverse("account_reset_password")

        # Verify email content
        self.assertIn("Welcome to Your Learning Journey!", email.body)
        self.assertIn(f"Hello {user.username}", email.body)
        self.assertIn(reset_url, email.body)
        self.assertIn(user.username, email.body)
        self.assertIn(user.email, email.body)

        # Verify HTML content
        self.assertTrue(hasattr(email, "alternatives"))
        html_content = email.alternatives[0][0]
        self.assertIn("Welcome to Your Learning Journey!", html_content)
        self.assertIn(f"Hello {user.username}", html_content)
        self.assertIn(reset_url, html_content)
        self.assertIn(user.username, html_content)
        self.assertIn(user.email, html_content)

        # Test case 2: User without email
        mail.outbox = []  # Clear the outbox
        user_no_email = User.objects.create_user(username="nomail", password="testpass123")
        with self.assertRaises(ValueError):
            send_welcome_email(user_no_email)
        self.assertEqual(len(mail.outbox), 0)  # No email should be sent


class PageLoadTests(BaseViewTest):
    """Test that all important pages load correctly"""

    def setUp(self):
        super().setUp()
        self.urls_to_test = {
            "index": reverse("index"),
            "subjects": reverse("subjects"),
            "learn": reverse("learn"),
            "teach": reverse("teach"),
            "course_search": reverse("course_search"),
            "cart": reverse("cart_view"),
        }
        self.authenticated_urls = {
            "student_dashboard": reverse("student_dashboard"),
        }

    def test_page_loads(self):
        """Test that each page loads with correct template and status code"""

        # Expected templates for each URL
        template_map = {
            "index": "index.html",
            "subjects": "subjects.html",
            "learn": "learn.html",
            "teach": "teach.html",
            "course_search": "courses/search.html",
            "cart": "cart/cart.html",
        }

        # Test each URL
        for name, url in self.urls_to_test.items():
            response = self.client.get(url)

            # Verify status code
            self.assertEqual(
                response.status_code, 200, f"Failed to load {name} page. Status code: {response.status_code}"
            )

            # Verify template
            self.assertTemplateUsed(response, template_map[name], f"Wrong template used for {name} page")

    def test_authenticated_page_loads(self):
        """Test pages that require authentication"""

        # Login as student
        self.client.login(username="student", password="studentpass123")

        # Test student dashboard
        response = self.client.get(self.authenticated_urls["student_dashboard"])
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/student.html")

    def test_unauthenticated_redirects(self):
        """Test that authenticated pages redirect when not logged in"""

        # Test student dashboard redirect
        response = self.client.get(self.authenticated_urls["student_dashboard"])
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))

    def test_form_pages_have_forms(self):
        """Test that pages with forms have the correct form in context"""

        # Test learn page
        response = self.client.get(self.urls_to_test["learn"])
        self.assertTrue("form" in response.context)
        self.assertIsInstance(response.context["form"], LearnForm)

        # Test teach page
        response = self.client.get(self.urls_to_test["teach"])
        self.assertTrue("form" in response.context)
        self.assertIsInstance(response.context["form"], TeachForm)

    def test_index_shows_recent_courses(self):
        """Test that index page shows 6 most recent published courses"""
        # Create 8 published courses with different creation times
        for i in range(8):
            Course.objects.create(
                title=f"Test Course {i}",
                description=f"Test Description {i}",
                teacher=self.teacher,
                learning_objectives=f"Test Objectives {i}",
                price=99.99,
                max_students=50,
                subject=self.subject,
                level="beginner",
                status="published",
                is_featured=(i < 3),  # Only first 3 are featured
            )

        # Get the index page
        response = self.client.get(self.urls_to_test["index"])
        self.assertEqual(response.status_code, 200)

        # Check that featured_courses contains 6 courses
        featured_courses = response.context["featured_courses"]
        self.assertEqual(len(featured_courses), 6)

        # Verify they are the 6 most recent courses (ordered by created_at descending)
        # The most recently created course should be first
        course_titles = [course.title for course in featured_courses]
        # Courses are created in order 0-7, so most recent should be 7, 6, 5, 4, 3, 2
        expected_titles = [f"Test Course {i}" for i in range(7, 1, -1)]
        self.assertEqual(course_titles, expected_titles)


class CourseInvitationTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a teacher
        self.teacher = User.objects.create_user(
            username="testteacher", email="teacher@test.com", password="testpass123"
        )
        # Create a subject
        self.subject = Subject.objects.create(name="Test Subject")
        # Create a course
        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.teacher,
            subject=self.subject,
            price=29.99,
            status="published",
            max_students=50,
        )
        self.invite_url = reverse("invite_student", args=[self.course.id])

    def test_invite_student_view_access(self):
        """Test that only the course teacher can access the invite view"""
        # Unauthenticated user should be redirected to login
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))

        # Create and login a non-teacher user
        User.objects.create_user(username="other", email="other@test.com", password="testpass123")
        self.client.login(username="other", password="testpass123")
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 302)  # Should be redirected
        self.assertTrue(response.url.startswith("/en/courses/"))

        # Teacher should have access
        self.client.login(username="testteacher", password="testpass123")
        response = self.client.get(self.invite_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/invite.html")

    def test_invite_student_send_invitation(self):
        """Test sending an invitation to a student"""
        self.client.login(username="testteacher", password="testpass123")

        # Send invitation
        data = {"email": "student@test.com", "message": "Please join my course!"}
        response = self.client.post(self.invite_url, data)

        # Check redirect
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("course_detail", args=[self.course.slug]))

        # Check that email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, f"Invitation to join {self.course.title}")
        self.assertEqual(email.to, ["student@test.com"])

        # Check email content
        self.assertIn(self.course.title, email.body)
        self.assertIn("Please join my course!", email.body)
        self.assertIn(str(self.course.price), email.body)

        # Verify success message
        messages = list(response.wsgi_request._messages)
        self.assertEqual(len(messages), 1)
        self.assertIn("Invitation sent", str(messages[0]))


class CourseDetailTests(TestCase):
    def setUp(self):
        """Set up test data for course detail tests"""
        self.client = Client()

        # Create users
        self.teacher = User.objects.create_user(username="teacher", email="teacher@test.com", password="testpass123")
        self.student = User.objects.create_user(username="student", email="student@test.com", password="testpass123")

        # Create subject
        self.subject = Subject.objects.create(
            name="Test Subject",
            slug="test-subject",
            description="Test Description",
        )

        # Create course
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.teacher,
            description="Test Description",
            learning_objectives="Test Objectives",
            prerequisites="Test Prerequisites",
            price=99.99,
            max_students=50,
            subject=self.subject,
            level="beginner",
            status="published",
            allow_individual_sessions=True,
        )

        # Create sessions
        now = timezone.now()
        self.future_session = Session.objects.create(
            course=self.course,
            title="Future Session",
            description="Future Session Description",
            start_time=now + timezone.timedelta(days=1),
            end_time=now + timezone.timedelta(days=1, hours=1),
            price=29.99,
            is_virtual=True,
            meeting_link="https://meet.test.com",
        )
        self.past_session = Session.objects.create(
            course=self.course,
            title="Past Session",
            description="Past Session Description",
            start_time=now - timezone.timedelta(days=1),
            end_time=now - timezone.timedelta(days=1, hours=1),
            price=29.99,
            location="Test Location",
        )

        # Create enrollment for student
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="approved",
        )

        # Create attendance for past session
        self.attendance = SessionAttendance.objects.create(
            student=self.student,
            session=self.past_session,
            status="completed",
        )

        # URL for detail page
        self.detail_url = reverse("course_detail", args=[self.course.slug])

    def test_course_detail_page_load(self):
        """Test course detail page loads for different user types"""
        # Test anonymous user
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/detail.html")

        # Test teacher
        self.client.login(username="teacher", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_teacher"])

        # Test enrolled student
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["enrollment"])
        self.assertFalse(response.context["is_teacher"])

    def test_course_information_display(self):
        """Test that course information is correctly displayed"""
        response = self.client.get(self.detail_url)
        self.assertEqual(response.context["course"], self.course)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.course.description)
        self.assertContains(response, self.course.learning_objectives)
        self.assertContains(response, self.course.prerequisites)
        self.assertContains(response, str(self.course.price))
        self.assertContains(response, self.course.get_level_display())
        self.assertContains(response, self.course.subject.name)

    def test_session_display(self):
        """
        Test that on the course detail page for a user who is not logged in or not enrolled:
        - Both session titles are shown.
        - The meeting link for the future virtual session is not visible.
        - The in-person session location and price for the future session are visible.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)

        # Both session titles should be present.
        self.assertContains(response, self.future_session.title)
        self.assertContains(response, self.past_session.title)

        # Verify that the future virtual session meeting link is NOT visible for non-enrolled/anonymous users.
        self.assertNotContains(response, self.future_session.meeting_link)

        # Verify that the in-person session's location is visible.
        self.assertContains(response, self.past_session.location)

        # Verify that the price for the future session is visible.
        self.assertContains(response, str(self.future_session.price))

    def test_teacher_specific_functionality(self):
        """Test functionality available only to teachers"""
        # Log in as teacher
        self.client.login(username="teacher", password="testpass123")

        # Get course detail page
        response = self.client.get(reverse("course_detail", args=[self.course.slug]))
        self.assertEqual(response.status_code, 200)

        # Check for course management links
        self.assertContains(response, reverse("update_course", args=[self.course.slug]))
        self.assertContains(response, reverse("course_progress_overview", args=[self.course.slug]))

    def test_enrolled_student_functionality(self):
        """Test functionality available to enrolled students"""
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)

        # Test enrollment status is shown
        self.assertContains(response, "You're enrolled!")

        # Test progress link is shown
        self.assertContains(response, reverse("student_dashboard"))

        # Test completed session is marked
        self.assertIn(self.past_session, response.context["completed_sessions"])
        self.assertContains(response, "Completed")

    def test_calendar_display(self):
        """Test that the session calendar is correctly displayed"""
        # Request the calendar for the month containing the session
        session_month = self.future_session.start_time.month
        session_year = self.future_session.start_time.year
        response = self.client.get(f"{self.detail_url}?month={session_month}&year={session_year}")

        # Test calendar context
        self.assertTrue("calendar_weeks" in response.context)
        self.assertTrue("today" in response.context)

        # Test session dates are marked
        calendar_weeks = response.context["calendar_weeks"]
        session_date = self.future_session.start_time.date()

        # Find the day in calendar that matches the session date
        session_day_found = False
        for week in calendar_weeks:
            for day in week:
                if day["date"] and day["date"] == session_date:
                    self.assertTrue(day["has_session"])
                    session_day_found = True
                    break
            if session_day_found:
                break

        self.assertTrue(session_day_found, "Session date not found in calendar")

    def test_session_completion_form(self):
        """Test session completion form for enrolled students"""
        self.client.login(username="student", password="testpass123")
        response = self.client.get(self.detail_url)

        # Past session should have completion form if not completed
        self.attendance.delete()  # Remove existing completion
        response = self.client.get(self.detail_url)
        self.assertContains(response, f'action="{reverse("mark_session_completed", args=[self.past_session.id])}"')

        # Future session should not have completion form
        self.assertNotContains(response, f'action="{reverse("mark_session_completed", args=[self.future_session.id])}"')

    def test_course_creation_by_non_teacher(self):
        """Test that any authenticated user can create a course"""
        regular_user = User.objects.create_user(username="regular_user", password="testpass123")
        if not hasattr(regular_user, "profile"):
            Profile.objects.create(user=regular_user, is_teacher=False)

        # Log in as regular user
        self.client.login(username="regular_user", password="testpass123")

        # Get CSRF token
        response = self.client.get(reverse("create_course"))
        self.assertEqual(response.status_code, 200)

        # Create a course
        data = {
            "title": "Test Course by Regular User",
            "description": "Test Description",
            "learning_objectives": "Test Objectives",
            "prerequisites": "Test Prerequisites",
            "price": "10.00",
            "max_students": "50",
            "level": "beginner",
            "subject": self.subject.id,
        }
        response = self.client.post(reverse("create_course"), data)

        # Should redirect to the new course's detail page
        self.assertEqual(response.status_code, 302)

        # Verify course was created
        course = Course.objects.get(title="Test Course by Regular User")
        self.assertEqual(course.teacher, regular_user)

    def test_course_creator_info_display(self):
        """Test that course creator info is displayed correctly"""
        # Add expertise to the teacher's profile
        self.teacher.profile.expertise = "Python Expert"
        self.teacher.profile.save()

        response = self.client.get(self.detail_url)

        # Test that the course creator section exists
        self.assertContains(response, "Course Creator")
        self.assertContains(response, self.teacher.username)
        self.assertContains(response, "Python Expert")

        # Test that expertise is optional
        self.teacher.profile.expertise = ""
        self.teacher.profile.save()
        response = self.client.get(self.detail_url)
        self.assertContains(response, "Course Creator")
        self.assertContains(response, self.teacher.username)

    def test_course_management_options(self):
        """Test that course management options are shown only to course creator"""
        creator = User.objects.create_user(username="creator", password="testpass123")
        if not hasattr(creator, "profile"):
            Profile.objects.create(user=creator, is_teacher=False)

        # Create a course as creator
        self.client.login(username="creator", password="testpass123")

        data = {
            "title": "Test Course",
            "description": "Test Description",
            "learning_objectives": "Test Objectives",
            "prerequisites": "Test Prerequisites",
            "price": "10.00",
            "max_students": "50",
            "level": "beginner",
            "subject": self.subject.id,
        }
        response = self.client.post(reverse("create_course"), data)
        self.assertEqual(response.status_code, 302)

        # Get the course by slug
        course = Course.objects.get(slug="test-course-1")

        # Check course detail page as creator
        response = self.client.get(reverse("course_detail", args=[course.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("update_course", args=[course.slug]))

        # Check course detail page as other user
        self.client.login(username="student", password="testpass123")
        response = self.client.get(reverse("course_detail", args=[course.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("update_course", args=[course.slug]))
