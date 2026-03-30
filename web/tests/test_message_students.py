# web/tests/test_message_students.py

from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase
from django.urls import reverse

from web.models import Course, Enrollment, Profile, Subject
from web.secure_messaging import decrypt_message


class MessageEnrolledStudentsTest(TestCase):
    def setUp(self):
        """Set up the test environment with teacher, students, and course."""
        # Create a teacher user
        self.teacher = User.objects.create_user(username="teacher", email="teacher@example.com", password="password123")
        self.teacher_profile, _ = Profile.objects.get_or_create(
            user=self.teacher,
            defaults={"is_teacher": True},
        )

        # Create student users
        self.student1 = User.objects.create_user(
            username="student1", email="student1@example.com", password="password123"
        )
        self.student1_profile, _ = Profile.objects.get_or_create(
            user=self.student1,
            defaults={"is_teacher": False},
        )

        self.student2 = User.objects.create_user(
            username="student2", email="student2@example.com", password="password123"
        )
        self.student2_profile, _ = Profile.objects.get_or_create(
            user=self.student2,
            defaults={"is_teacher": False},
        )

        self.subject = Subject.objects.create(name="Test Subject")

        # Create a course taught by the teacher
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.teacher,
            description="Test course description",
            price=0,
            max_students=30,
            subject=self.subject,
            level="beginner",
        )

        # Enroll students in the course
        Enrollment.objects.create(student=self.student1, course=self.course, status="approved")
        Enrollment.objects.create(student=self.student2, course=self.course, status="approved")

        # Set up the client and login as teacher
        self.client = Client()
        self.client.login(username="teacher", password="password123")

        # URL for message_enrolled_students view
        self.url = reverse("message_students", kwargs={"slug": self.course.slug})

    def test_get_message_form(self):
        """Test that the message form is displayed with enrolled students."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student1.username)
        self.assertContains(response, self.student2.username)
        self.assertContains(response, "All Enrolled Students")

    def test_send_message_to_all_students(self):
        """Test sending a message to all enrolled students."""
        # Clear the mail outbox
        mail.outbox = []

        # Send a message to all enrolled students
        message_data = {
            "title": "Test message to all",
            "message": "This is a test message to all students",
            "student_id": "all",
        }
        response = self.client.post(self.url, message_data)

        # Check redirection to course_detail page
        self.assertRedirects(response, reverse("course_detail", kwargs={"slug": self.course.slug}))
        # Two emails should be sent (one per student)
        self.assertEqual(len(mail.outbox), 2)

        # Verify that emails are sent to the correct recipients
        recipients = [email.to[0] for email in mail.outbox]
        self.assertIn(self.student1.email, recipients)
        self.assertIn(self.student2.email, recipients)

        # Verify that each email subject contains the course title and message title,
        # and that the email body is encrypted, so decrypting it matches the original message.
        for email in mail.outbox:
            self.assertIn(self.course.title, email.subject)
            self.assertIn(message_data["title"], email.subject)
            self.assertTrue(email.body)
            self.assertNotEqual(email.body, message_data["message"])
            try:
                decrypted_email = decrypt_message(email.body.encode("utf-8"))
                self.assertEqual(decrypted_email, message_data["message"])
            except (ValueError, TypeError) as e:  # Specify expected exception types
                self.fail(f"Failed to decrypt email content: {e}")

    def test_send_message_to_specific_student(self):
        """Test sending a message to a specific student."""
        # Clear the mail outbox
        mail.outbox = []

        # Send a message to student1
        message_data = {
            "title": "Test message to student1",
            "message": "This is a test message to student1",
            "student_id": str(self.student1.id),
        }
        response = self.client.post(self.url, message_data)

        # Check redirection to course_detail page
        self.assertRedirects(response, reverse("course_detail", kwargs={"slug": self.course.slug}))
        # Only one email should be sent
        self.assertEqual(len(mail.outbox), 1)
        # Verify the email is sent to student1
        self.assertEqual(mail.outbox[0].to[0], self.student1.email)
        self.assertIn(self.course.title, mail.outbox[0].subject)
        self.assertIn(message_data["title"], mail.outbox[0].subject)
        self.assertTrue(mail.outbox[0].body)
        self.assertNotEqual(mail.outbox[0].body, message_data["message"])
        try:
            decrypted_email = decrypt_message(mail.outbox[0].body.encode("utf-8"))
            self.assertEqual(decrypted_email, message_data["message"])
        except (ValueError, TypeError) as e:  # Specify expected exception types
            self.fail(f"Failed to decrypt email content: {e}")

    def test_send_message_to_nonexistent_student(self):
        """Test sending a message to a non-existent student."""
        # Clear the mail outbox
        mail.outbox = []

        # Attempt to send a message to a non-existent student
        message_data = {
            "title": "Test message to non-existent student",
            "message": "This is a test message",
            "student_id": "999",  # Non-existent ID
        }
        response = self.client.post(self.url, message_data)
        # Should redirect back to the message form
        self.assertRedirects(response, self.url)
        # Ensure that no emails are sent
        self.assertEqual(len(mail.outbox), 0)

    def test_unauthenticated_user_cannot_access(self):
        """Test that unauthenticated users cannot access the view."""
        self.client.logout()
        response = self.client.get(self.url)
        login_url = reverse("account_login")
        self.assertTrue(response.url.startswith(login_url))

    def test_non_teacher_cannot_access(self):
        """Test that non-teacher users cannot access the view."""
        self.client.logout()
        self.client.login(username="student1", password="password123")
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)
