from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.forms import TeachForm
from web.models import Course, Profile, Session, Subject


class TeachViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.teach_url = reverse("teach")

        # Create a test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.user_profile, _ = Profile.objects.get_or_create(user=self.user)

        # Create a test subject
        self.subject = Subject.objects.create(name="General", slug="general")

        # Create a test image file to use in all tests
        self.test_image = SimpleUploadedFile(
            "test_image.jpg",
            # Minimal valid JPEG image (1x1 pixel, black)
            (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03"
                b"\x04\x05\x08\x05\x05\x04\x04\x05\x0a\x07\x07\x06\x08\x0c\x0a\x0c\x0c"
                b"\x0b\x0a\x0b\x0b\x0d\x0e\x12\x10\x0d\x0e\x11\x0e\x0b\x0b\x10\x16\x10"
                b"\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14"
                b"\xff\xdb\x00C\x01\x03\x04\x04\x05\x04\x05\x09\x05\x05\x09\x14\x0d\x0b"
                b"\x0d\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b"\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b"\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11'
                b"\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
                b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04"
                b'\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x14'
                b"2\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\x09\x0a\x16\x17\x18"
                b"\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84"
                b"\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3"
                b"\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2"
                b"\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda"
                b"\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7"
                b"\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfd"
                b"\xf2\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02"
                b"\xff\xd9"
            ),
            content_type="image/jpeg",
        )

    def get_test_image(self):
        """Get a fresh copy of the test image for each test"""
        # Need to create a new file for each test because the file position is consumed after first use
        return SimpleUploadedFile(
            "test_image.jpg",
            # Minimal valid JPEG image (1x1 pixel, black)
            (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00\x03\x02\x02\x03\x02\x02\x03\x03\x03\x03\x04\x03\x03"
                b"\x04\x05\x08\x05\x05\x04\x04\x05\x0a\x07\x07\x06\x08\x0c\x0a\x0c\x0c"
                b"\x0b\x0a\x0b\x0b\x0d\x0e\x12\x10\x0d\x0e\x11\x0e\x0b\x0b\x10\x16\x10"
                b"\x11\x13\x14\x15\x15\x15\x0c\x0f\x17\x18\x16\x14\x18\x12\x14\x15\x14"
                b"\xff\xdb\x00C\x01\x03\x04\x04\x05\x04\x05\x09\x05\x05\x09\x14\x0d\x0b"
                b"\x0d\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b"\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b"\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14\x14"
                b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11'
                b"\x01\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
                b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04"
                b'\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x14'
                b"2\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\x09\x0a\x16\x17\x18"
                b"\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84"
                b"\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3"
                b"\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2"
                b"\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda"
                b"\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7"
                b"\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xfd"
                b"\xf2\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02\x8a(\xa0\x02"
                b"\xff\xd9"
            ),
            content_type="image/jpeg",
        )

    def test_get_teach_page(self):
        """Test GET request renders teach page with form"""
        response = self.client.get(self.teach_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "teach.html")
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], TeachForm)

    def test_get_teach_with_subject_param(self):
        """Test GET with subject parameter initializes form"""
        response = self.client.get(self.teach_url, {"subject": "Python"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"].initial["course_title"], "Python")

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_authenticated_valid(self, mock_captcha):
        """Test POST for authenticated user with valid data"""
        self.client.login(username="testuser", password="testpass123")

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "test@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        # Add the required image file
        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 302)

        course = Course.objects.get(title="Test Course")
        self.assertEqual(course.teacher, self.user)
        self.assertEqual(course.status, "draft")
        self.assertEqual(course.subject, self.subject)
        self.assertTrue(Session.objects.filter(course=course).exists())
        self.assertEqual(response.url, reverse("course_detail", kwargs={"slug": course.slug}))

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_form_for_authenticated_user(self, mock_captcha):
        """Test form behavior for authenticated users - no email or captcha required"""
        self.client.login(username="testuser", password="testpass123")

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        # For authenticated users, we expect a successful submission without email/captcha
        self.assertEqual(response.status_code, 302)  # Successful redirect

        # Verify a course is created with the authenticated user's email
        course = Course.objects.get(title="Test Course")
        self.assertEqual(course.teacher, self.user)

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_authenticated_duplicate_title(self, mock_captcha):
        """Test POST for authenticated user with duplicate course title"""
        self.client.login(username="testuser", password="testpass123")

        Course.objects.create(
            title="Test Course",
            description="Existing course",
            teacher=self.user,
            price=0,
            max_students=12,
            status="draft",
            subject=self.subject,
        )

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "test@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("You already have a course with this title", str(response.context["form"].errors))

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    @patch("web.views.send_email_confirmation")
    @patch("web.views.send_welcome_teach_course_email")
    def test_post_unauthenticated_new_user(self, mock_welcome_email, mock_email_confirmation, mock_captcha):
        """Test POST for unauthenticated user creating new account"""
        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "newuser@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_email_verification_sent"))

        user = User.objects.get(email="newuser@example.com")
        self.assertTrue(Profile.objects.get(user=user).is_teacher)
        self.assertTrue(Course.objects.filter(title="Test Course", teacher=user).exists())
        self.assertTrue(EmailAddress.objects.filter(user=user, email="newuser@example.com", verified=False).exists())
        self.assertIn("pending_course_id", self.client.session)

        mock_email_confirmation.assert_called()
        mock_welcome_email.assert_called()

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_unauthenticated_existing_verified(self, mock_captcha):
        """Test POST for unauthenticated user with existing verified email"""
        existing_user = User.objects.create_user(
            username="existing", email="existing@example.com", password="existpass123"
        )
        EmailAddress.objects.create(user=existing_user, email="existing@example.com", primary=True, verified=True)

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "existing@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Course.objects.filter(title="Test Course").exists())
        self.assertEqual(response.url, reverse("account_login"))

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    @patch("web.views.send_email_confirmation")
    def test_post_unauthenticated_existing_unverified(self, mock_email_confirmation, mock_captcha):
        """Test POST for unauthenticated user with existing unverified email"""
        existing_user = User.objects.create_user(
            username="existing", email="existing@example.com", password="existpass123"
        )
        EmailAddress.objects.create(user=existing_user, email="existing@example.com", primary=True, verified=False)

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "existing@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("account_login"))
        mock_email_confirmation.assert_called()

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_with_image(self, mock_captcha):
        """Test POST with image upload"""
        self.client.login(username="testuser", password="testpass123")

        image = self.get_test_image()

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "test@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": "on",
            "course_image": image,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, form_data)
        if response.status_code != 302:
            if hasattr(response, "context") and response.context is not None:
                print("Form errors:", response.context.get("form", {}).errors)
            else:
                print("Response status:", response.status_code)
                print("Response content:", response.content.decode())
        self.assertEqual(response.status_code, 302)
        course = Course.objects.get(title="Test Course")
        self.assertTrue(course.image)

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_invalid_form(self, mock_captcha):
        """Test POST with invalid form data"""
        form_data = {
            "course_title": "",  # Invalid: empty title
            "course_description": "This is a test course",
            "email": "test@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("course_title", response.context["form"].errors)

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_past_session_time(self, mock_captcha):
        """Test POST with past preferred session time"""
        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "test@example.com",
            "preferred_session_times": (timezone.now() - timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertIn("preferred_session_times", response.context["form"].errors)

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    def test_post_unauthenticated_duplicate_unverified(self, mock_captcha):
        """Test POST for unauthenticated user with duplicate title but unverified email"""
        existing_user = User.objects.create_user(
            username="existing", email="existing@example.com", password="existpass123"
        )
        EmailAddress.objects.create(user=existing_user, email="existing@example.com", primary=True, verified=False)
        Course.objects.create(
            title="Test Course",
            description="Existing course",
            teacher=existing_user,
            price=0,
            max_students=12,
            status="draft",
            subject=self.subject,
        )

        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "existing@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Course.objects.filter(title="Test Course", teacher=existing_user).count(), 1)
        self.assertIn("pending_course_id", self.client.session)

    @patch("captcha.fields.CaptchaField.clean", return_value="PASSED")
    @patch("web.views.send_welcome_teach_course_email", side_effect=Exception("Email error"))
    def test_post_new_user_email_failure(self, mock_welcome_email, mock_captcha):
        """Test POST when welcome email fails"""
        form_data = {
            "course_title": "Test Course",
            "course_description": "This is a test course",
            "email": "newuser@example.com",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "captcha": "dummy",
        }

        response = self.client.post(self.teach_url, {**form_data, "course_image": self.get_test_image()})

        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())
