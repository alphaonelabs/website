from unittest.mock import patch

from django import forms
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from web.forms import (
    CourseCreationForm,
    CourseMaterialForm,
    ProfileUpdateForm,
    SessionForm,
    TeachForm,
    UserRegistrationForm,
)
from web.forms_additional import (
    BlogCommentForm,
    CourseReviewForm,
    CourseSearchForm,
    CourseUpdateForm,
    LearningInquiryForm,
    MessageForm,
    StudyGroupForm,
    TeachingInquiryForm,
    TopicCreationForm,
)
from web.models import Course, ForumCategory, Subject, User


@override_settings(
    STRIPE_SECRET_KEY="dummy_key",
    ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE=True,
)
class UserRegistrationFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock stripe module
        cls.stripe_patcher = patch("web.views.stripe")
        cls.mock_stripe = cls.stripe_patcher.start()
        # Mock CAPTCHA field
        cls.captcha_patcher = patch(
            "captcha.fields.CaptchaField.clean",
            side_effect=forms.ValidationError("Invalid captcha"),
        )
        cls.mock_captcha = cls.captcha_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.stripe_patcher.stop()
        cls.captcha_patcher.stop()
        super().tearDownClass()

    def test_valid_registration_form(self):
        """Test user registration with valid data"""
        # Create a user and get their automatically created profile
        existing_user = User.objects.create_user(
            username="existing_user", email="existing@example.com", password="testpass123"
        )
        # Set the referral code on the automatically created profile
        existing_user.profile.referral_code = "TEST123"
        existing_user.profile.save()

        # For valid test, allow captcha to pass
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "testpass123",
            "is_teacher": False,
            "is_profile_public": False,
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
            "referral_code": "TEST123",
        }
        form = UserRegistrationForm(data=form_data)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())

    def test_invalid_registration_form(self):
        """Test user registration with invalid data"""
        # For invalid test, make captcha fail
        self.mock_captcha.side_effect = forms.ValidationError("Invalid captcha")

        # Test with mismatched passwords
        form_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "first_name": "New",
            "last_name": "User",
            "password1": "testpass123",
            "password2": "differentpass123",  # Different password
            "is_teacher": False,
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Invalid captcha", str(form.errors))

        # Test with invalid email
        form_data.update(
            {
                "email": "invalid-email",
                "password2": "testpass123",  # Fix password to isolate email validation
            }
        )
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Enter a valid email address", str(form.errors))

        # Test with missing required field
        form_data_without_email = form_data.copy()
        form_data_without_email.pop("email")  # Remove required field
        form = UserRegistrationForm(data=form_data_without_email)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required", str(form.errors))


@override_settings(STRIPE_SECRET_KEY="dummy_key")
class CourseCreationFormTests(TestCase):
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
        self.User = get_user_model()
        self.teacher = self.User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        # Update existing profile instead of creating a new one
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        # Create a test subject
        self.subject = Subject.objects.create(
            name="Programming5",
            slug="programming5",
            description="Programming courses",
            icon="fas fa-code",
        )

    def test_valid_course_creation_form(self):
        """Test course creation with valid data"""
        form_data = {
            "title": "New Course",
            "description": "Course Description",
            "learning_objectives": "Course Objectives",
            "price": 99.99,
            "max_students": 50,
            "subject": self.subject.id,  # Use subject ID instead of string
            "level": "beginner",
            "teacher": self.teacher.id,
        }
        form = CourseCreationForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_course_creation_form(self):
        """Test course creation with invalid data"""
        # Test with negative price
        form_data = {
            "title": "New Course",
            "description": "Course Description",
            "learning_objectives": "Course Objectives",
            "price": -99.99,
            "max_students": 50,
            "subject": self.subject.id,  # Use subject ID instead of string
            "level": "beginner",
            "teacher": self.teacher.id,
        }
        form = CourseCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

        # Test with invalid subject
        form_data["price"] = 99.99
        form_data["subject"] = 999  # Use non-existent subject ID
        form = CourseCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("subject", form.errors)


class SessionFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.user.profile.is_teacher = True
        self.user.profile.save()

        self.subject = Subject.objects.create(
            name="Programming Sessions",
            slug="programming-sessions",
            description="Programming courses for sessions",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.user,
            price=50.00,
            max_students=50,
            subject=self.subject,
            level="beginner",
            status="draft",
        )

    def test_valid_session_form(self):
        form_data = {
            "title": "Week 1 Introduction",
            "description": "Introduction to the course",
            "start_time": timezone.now() + timezone.timedelta(days=1),
            "end_time": timezone.now() + timezone.timedelta(days=1, hours=2),
            "is_virtual": True,
            "meeting_link": "https://zoom.us/j/123456789",
        }
        form = SessionForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_session_form(self):
        # Test with end time before start time
        form_data = {
            "title": "Week 1 Introduction",
            "description": "Introduction to the course",
            "start_time": timezone.now() + timezone.timedelta(days=1),
            "end_time": timezone.now(),  # End time before start time
            "is_virtual": True,
            "meeting_link": "https://zoom.us/j/123456789",
        }
        form = SessionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("End time must be after start time", str(form.errors))

    def test_invalid_virtual_session(self):
        # Test virtual session without meeting link
        form_data = {
            "title": "Week 1 Introduction",
            "description": "Introduction to the course",
            "start_time": timezone.now() + timezone.timedelta(days=1),
            "end_time": timezone.now() + timezone.timedelta(days=1, hours=2),
            "is_virtual": True,
            "meeting_link": "",  # Missing meeting link for virtual session
        }
        form = SessionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Meeting link is required for virtual sessions", str(form.errors))


class CourseSearchFormTests(TestCase):
    def test_valid_search_form(self):
        form_data = {
            "query": "python",
            "subject": "",
            "level": "beginner",
            "price_min": "10.00",
            "price_max": "50.00",
        }
        form = CourseSearchForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_search_form(self):
        form_data = {
            "query": "python",
            "subject": "",
            "level": "invalid_level",
            "price_min": "abc",
            "price_max": "def",
        }
        form = CourseSearchForm(data=form_data)
        self.assertFalse(form.is_valid())

    def test_invalid_price_range(self):
        form_data = {
            "query": "python",
            "subject": "",
            "level": "beginner",
            "price_min": "50.00",
            "price_max": "10.00",
        }
        form = CourseSearchForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("Minimum price cannot be greater than maximum price", form.errors["__all__"])


class CourseUpdateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.user.profile.is_teacher = True
        self.user.profile.save()

        self.subject = Subject.objects.create(
            name="Programming Updates",
            slug="programming-updates",
            description="Programming courses for updates",
        )

        self.course = Course.objects.create(
            title="Test Course",
            description="Test Description",
            teacher=self.user,
            price=50.00,
            max_students=50,
            subject=self.subject,
            level="beginner",
            status="draft",
        )

    def test_valid_update_form(self):
        form_data = {
            "title": "Updated Course",
            "description": "Updated Description",
            "learning_objectives": "Updated Objectives",
            "prerequisites": "Updated Prerequisites",
            "price": 75.00,
            "max_students": 75,
            "subject": self.subject.id,
            "level": "intermediate",
            "status": "published",
        }
        form = CourseUpdateForm(data=form_data, instance=self.course)
        self.assertTrue(form.is_valid())

    def test_invalid_update_form(self):
        form_data = {
            "title": "",  # Title is required
            "description": "Updated Description",
            "price": -10,  # Invalid price
            "max_students": -5,  # Invalid max_students
            "subject": 999,  # Invalid subject ID
            "level": "invalid_level",  # Invalid level
            "status": "invalid_status",  # Invalid status
        }
        form = CourseUpdateForm(data=form_data, instance=self.course)
        self.assertFalse(form.is_valid())


class CourseReviewFormTests(TestCase):
    def test_valid_review_form(self):
        """Test course review with valid data"""
        form_data = {
            "rating": 5,
            "comment": "Great course!",
        }
        form = CourseReviewForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_review_form(self):
        """Test course review with invalid data"""
        form_data = {
            "rating": 6,  # Invalid rating
            "comment": "",  # Comment required
        }
        form = CourseReviewForm(data=form_data)
        self.assertFalse(form.is_valid())


class MaterialUploadFormTests(TestCase):
    def test_valid_upload_form(self):
        """Test material upload with valid data"""
        test_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        form_data = {
            "title": "Lecture Notes",
            "description": "Week 1 lecture notes",
            "material_type": "document",
            "order": 1,
        }
        form = CourseMaterialForm(data=form_data, files={"file": test_file})
        self.assertTrue(form.is_valid())

    def test_invalid_upload_form(self):
        """Test material upload with invalid data"""
        form_data = {
            "title": "",  # Title is required
            "description": "Test description",
            "material_type": "invalid_type",  # Invalid type
            "order": -1,  # Invalid order
        }
        form = CourseMaterialForm(data=form_data)
        self.assertFalse(form.is_valid())


class TopicCreationFormTests(TestCase):
    def setUp(self):
        self.category = ForumCategory.objects.create(name="General Discussion")

    def test_valid_topic_form(self):
        """Test topic creation with valid data"""
        form_data = {
            "title": "New Topic",
            "content": "Topic content here",
        }
        form = TopicCreationForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_topic_form(self):
        """Test topic creation with invalid data"""
        form_data = {
            "title": "",  # Title required
            "content": "",  # Content required
        }
        form = TopicCreationForm(data=form_data)
        self.assertFalse(form.is_valid())


class StudyGroupFormTests(TestCase):
    def test_valid_group_form(self):
        """Test study group creation with valid data"""
        form_data = {
            "name": "Python Study Group",
            "description": "Weekly study sessions",
            "max_members": 10,
            "is_private": False,
        }
        form = StudyGroupForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_group_form(self):
        """Test study group creation with invalid data"""
        form_data = {
            "name": "",  # Name required
            "max_members": 1,  # Too few members
        }
        form = StudyGroupForm(data=form_data)
        self.assertFalse(form.is_valid())


class BlogCommentFormTests(TestCase):
    def test_valid_comment_form(self):
        """Test blog comment with valid data"""
        form_data = {
            "content": "Great article!",
        }
        form = BlogCommentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_comment_form(self):
        """Test blog comment with invalid data"""
        form_data = {
            "content": "",  # Content required
        }
        form = BlogCommentForm(data=form_data)
        self.assertFalse(form.is_valid())


class MessageFormTests(TestCase):
    def test_valid_message_form(self):
        """Test message with valid data"""
        form_data = {
            "content": "Hello there!",
        }
        form = MessageForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_message_form(self):
        """Test message with invalid data"""
        form_data = {
            "content": "",  # Content required
        }
        form = MessageForm(data=form_data)
        self.assertFalse(form.is_valid())


class LearningInquiryFormTests(TestCase):
    def test_valid_inquiry_form(self):
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "subject_interest": "Python Programming",
            "learning_goals": "I want to learn web development",
            "preferred_schedule": "Weekends",
            "experience_level": "beginner",
        }
        form = LearningInquiryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_inquiry_form(self):
        form_data = {
            "name": "",  # Name is required
            "email": "invalid-email",  # Invalid email
            "subject_interest": "",  # Subject interest is required
            "learning_goals": "",  # Learning goals are required
            "preferred_schedule": "",  # Schedule is required
            "experience_level": "invalid_level",  # Invalid level
        }
        form = LearningInquiryForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("subject_interest", form.errors)
        self.assertIn("learning_goals", form.errors)
        self.assertIn("preferred_schedule", form.errors)
        self.assertIn("experience_level", form.errors)


class TeachingInquiryFormTests(TestCase):
    def test_valid_inquiry_form(self):
        """Test teaching inquiry with valid data"""
        form_data = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "expertise": "Machine Learning",
            "experience": "5 years teaching experience",
        }
        form = TeachingInquiryForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_inquiry_form(self):
        """Test teaching inquiry with invalid data"""
        form_data = {
            "name": "",  # Name required
            "email": "invalid-email",  # Invalid email
        }
        form = TeachingInquiryForm(data=form_data)
        self.assertFalse(form.is_valid())


class ProfileUpdateFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        # Create a small valid GIF file (1x1 transparent pixel)
        gif_content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        self.test_image = SimpleUploadedFile(name="test_avatar.gif", content=gif_content, content_type="image/gif")

    def test_valid_profile_form(self):
        """Test profile update with valid data"""
        form_data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "expertise": "Python, Django",
            "is_profile_public": False,  # explicitly set the field
        }
        form_files = {"avatar": self.test_image}
        form = ProfileUpdateForm(data=form_data, files=form_files, instance=self.user)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_valid_profile_form_without_avatar(self):
        """Test profile update with valid data but no avatar"""
        form_data = {
            "username": "testuser",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "bio": "Python developer",
            "expertise": "Python, Django",
            "is_profile_public": False,  # explicitly set the field
        }
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_profile_form(self):
        """Test profile update with invalid data"""
        form_data = {
            "email": "invalid-email",  # Invalid email
        }
        form = ProfileUpdateForm(data=form_data, instance=self.user)
        self.assertFalse(form.is_valid())


class TeachFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Mock CAPTCHA field
        cls.captcha_patcher = patch(
            "captcha.fields.CaptchaField.clean",
            side_effect=forms.ValidationError("Invalid captcha"),
        )
        cls.mock_captcha = cls.captcha_patcher.start()

    @classmethod
    def tearDownClass(cls):
        cls.captcha_patcher.stop()
        super().tearDownClass()

    def setUp(self):
        self.User = get_user_model()
        # Create a test user
        self.user = self.User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )
        # Create a test subject
        self.subject = Subject.objects.create(
            name="Programming",
            slug="programming",
            description="Programming courses",
            icon="fas fa-code",
        )

    def test_valid_form_unauthenticated(self):
        """Test TeachForm with valid data for an unauthenticated user."""
        # Allow CAPTCHA to pass for valid test
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        # Create a small valid GIF file (1x1 transparent pixel)
        gif_content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        test_image = SimpleUploadedFile(name="test_image.gif", content=gif_content, content_type="image/gif")
        form_files = {"course_image": test_image}

        form = TeachForm(data=form_data, files=form_files)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_valid_form_authenticated(self):
        """Test TeachForm with valid data for an authenticated user."""
        # Allow CAPTCHA to pass for valid test
        self.mock_captcha.side_effect = lambda x: True

        # For an authenticated user, the email must match the user's email
        # (this is validated in the teach function, not the form)
        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "testuser@example.com",  # Must match the user's email
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        test_image = SimpleUploadedFile(
            name="test_image.gif",
            content=(
                b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
                b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01"
                b"\x00\x00\x02\x02D\x01\x00;"
            ),
            content_type="image/gif",
        )
        form_files = {"course_image": test_image}

        form = TeachForm(data=form_data, files=form_files)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_invalid_form_missing_required_fields(self):
        """Test TeachForm with missing required fields."""
        # Allow CAPTCHA to pass to isolate other validation errors
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "",  # Missing required field
            "course_description": "",  # Missing required field
            "preferred_session_times": "",
            "flexible_timing": False,
            "email": "",  # Missing required field
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = TeachForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("course_title", form.errors)
        self.assertIn("course_description", form.errors)
        self.assertIn("email", form.errors)
        self.assertIn("This field is required", str(form.errors))

    def test_invalid_course_title(self):
        """Test TeachForm with invalid course_title (special characters)."""
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "Introduction@Python!",  # Invalid characters
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = TeachForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("course_title", form.errors)
        self.assertIn("Title can only contain letters, numbers, spaces, and hyphens", str(form.errors))

    def test_invalid_course_image_size(self):
        """Test TeachForm with an image file that exceeds the size limit."""
        self.mock_captcha.side_effect = lambda x: True

        # Create a large but valid GIF file (6MB, exceeding the 5MB limit)
        # Start with a valid 1x1 GIF image
        gif_content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        # Pad the content to make it 6MB
        padding = b"0" * (6 * 1024 * 1024 - len(gif_content))
        large_gif_content = gif_content + padding
        large_image = SimpleUploadedFile(name="large_image.gif", content=large_gif_content, content_type="image/gif")
        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form_files = {"course_image": large_image}

        form = TeachForm(data=form_data, files=form_files)
        self.assertFalse(form.is_valid())
        self.assertIn("course_image", form.errors)
        self.assertIn("Image must be less than 5MB", str(form.errors))

    def test_invalid_course_image_extension(self):
        """Test TeachForm with an image file with an invalid extension."""
        self.mock_captcha.side_effect = lambda x: True

        # Use a valid GIF image but with an invalid extension (.txt)
        gif_content = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!"
            b"\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        invalid_image = SimpleUploadedFile(name="invalid_image.txt", content=gif_content, content_type="text/plain")
        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form_files = {"course_image": invalid_image}

        form = TeachForm(data=form_data, files=form_files)
        self.assertFalse(form.is_valid())
        self.assertIn("course_image", form.errors)
        self.assertIn("File extension", str(form.errors))

    def test_invalid_captcha(self):
        """Test TeachForm with invalid CAPTCHA."""
        # CAPTCHA mock is already set to fail by default
        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = TeachForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("captcha", form.errors)
        self.assertIn("Invalid captcha", str(form.errors))

    def test_invalid_email_format(self):
        """Test TeachForm with invalid email format for unauthenticated user."""
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "invalid-email",  # Invalid email format
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = TeachForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("Enter a valid email address", str(form.errors))

    def test_invalid_preferred_session_times(self):
        """Test TeachForm with invalid preferred_session_times (past date)."""
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() - timezone.timedelta(days=1)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),  # Past date
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        form = TeachForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("preferred_session_times", form.errors)
        self.assertIn("Preferred session time cannot be in the past", str(form.errors))

    def test_missing_course_image(self):
        """Test TeachForm with no course_image provided when required=True."""
        self.mock_captcha.side_effect = lambda x: True

        form_data = {
            "course_title": "Introduction to Python",
            "course_description": "A beginner-friendly Python course.",
            "preferred_session_times": (timezone.now() + timezone.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"),
            "flexible_timing": True,
            "email": "newuser@example.com",
            "captcha_0": "dummy-hash",
            "captcha_1": "PASSED",
        }
        # Explicitly no files provided
        form = TeachForm(data=form_data, files={})
        self.assertFalse(form.is_valid())
        self.assertIn("course_image", form.errors)
        self.assertIn("This field is required", str(form.errors))
