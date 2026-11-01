from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from web.models import Course, CourseMaterial, Enrollment, NotificationPreference, Subject
from web.notifications import send_assignment_reminders


class SendAssignmentRemindersTest(TestCase):
    def setUp(self):
        # Create teacher and student accounts.
        self.teacher = User.objects.create_user(username="teacher", email="teacher@example.com", password="pass")
        self.student = User.objects.create_user(username="testuser", email="testuser@example.com", password="pass")
        # Create a subject.
        self.subject = Subject.objects.create(name="Test Subject")
        # Create a course with required fields.
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            price=Decimal("10.00"),
            max_students=100,
            teacher=self.teacher,
            subject=self.subject,
        )
        # Enroll the student with approved status.
        Enrollment.objects.create(course=self.course, student=self.student, status="approved")
        # Create notification preferences for the student.
        NotificationPreference.objects.get_or_create(
            user=self.student,
            defaults={
                "reminder_days_before": 3,
                "reminder_hours_before": 24,
                "email_notifications": True,
                "in_app_notifications": True,
            },
        )

    @patch("web.notifications.send_mail")
    @patch("web.notifications.send_notification")
    def test_early_reminder(self, mock_send_notification, mock_send_mail):
        """
        Test that an assignment due within the early window triggers early reminder notifications.
        """
        assignment = CourseMaterial.objects.create(
            course=self.course,
            title="Early Reminder Assignment",
            material_type="assignment",
            due_date=timezone.now() + timedelta(days=2),  # Within early window
            external_url="http://example.com/assignment",
            reminder_sent=False,
            final_reminder_sent=False,
        )
        send_assignment_reminders()
        assignment.refresh_from_db()
        self.assertTrue(assignment.reminder_sent, "Early reminder should be marked as sent.")
        self.assertTrue(mock_send_notification.called, "In-app notification should be sent for early reminder.")
        self.assertTrue(mock_send_mail.called, "Email notification should be sent for early reminder.")

    @patch("web.notifications.send_mail")
    @patch("web.notifications.send_notification")
    def test_final_reminder(self, mock_send_notification, mock_send_mail):
        """
        Test that an assignment due within the final window triggers final reminder notifications.
        """
        assignment = CourseMaterial.objects.create(
            course=self.course,
            title="Final Reminder Assignment",
            material_type="assignment",
            due_date=timezone.now() + timedelta(hours=20),  # Within final window (20 hours from now)
            external_url="http://example.com/assignment",
            reminder_sent=True,  # Early reminder already sent.
            final_reminder_sent=False,  # Final reminder not yet sent.
        )
        mock_send_notification.reset_mock()
        mock_send_mail.reset_mock()
        send_assignment_reminders()
        assignment.refresh_from_db()
        self.assertTrue(assignment.final_reminder_sent, "Final reminder should be marked as sent.")
        self.assertTrue(mock_send_notification.called, "In-app notification should be sent for final reminder.")
        self.assertTrue(mock_send_mail.called, "Email notification should be sent for final reminder.")

    @patch("web.notifications.send_mail")
    @patch("web.notifications.send_notification")
    def test_no_reminder(self, mock_send_notification, mock_send_mail):
        """
        Test that an assignment outside the reminder window does not trigger notifications.
        """
        assignment = CourseMaterial.objects.create(
            course=self.course,
            title="No Reminder Assignment",
            material_type="assignment",
            due_date=timezone.now() + timedelta(days=5),  # Outside early window
            external_url="http://example.com/assignment",
            reminder_sent=False,
            final_reminder_sent=False,
        )
        send_assignment_reminders()
        assignment.refresh_from_db()
        self.assertFalse(
            assignment.reminder_sent, "Early reminder should not be marked for assignments outside the window."
        )
        self.assertFalse(
            assignment.final_reminder_sent, "Final reminder should not be marked for assignments outside the window."
        )
        self.assertFalse(mock_send_notification.called, "No in-app notification should be sent.")
        self.assertFalse(mock_send_mail.called, "No email notification should be sent.")
