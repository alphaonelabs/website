"""
Tests for assignment deadline reminder system.

Tests the automatic sending of reminder emails when assignments are due soon,
using Django signals and the ReminderScheduler class.
"""

from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from web.models import Course, CourseMaterial, Enrollment, Subject
from web.assignment_reminders import ReminderScheduler

User = get_user_model()


class ReminderSchedulerTests(TestCase):
    """Test the ReminderScheduler class logic."""

    def setUp(self):
        """Set up test data."""
        self.subject = Subject.objects.create(
            name="Computer Science",
            slug="computer-science"
        )
        
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        self.course = Course.objects.create(
            title="Python 101",
            slug="python-101",
            teacher=self.teacher,
            description="Learn Python basics",
            learning_objectives="Know Python",
            price=99.99,
            max_students=30,
            subject=self.subject
        )

        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="testpass123"
        )

        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            status="approved"
        )

    def test_should_send_early_reminder_when_due_in_24_hours(self):
        """Test early reminder should be sent when deadline is 24-48 hours away."""
        due_date = timezone.now() + timedelta(hours=36)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date
        )

        self.assertTrue(ReminderScheduler.should_send_early_reminder(material))

    def test_should_not_send_early_reminder_when_already_sent(self):
        """Test early reminder not sent if already marked as sent."""
        due_date = timezone.now() + timedelta(hours=36)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date,
            reminder_sent=True  # Already sent
        )

        self.assertFalse(ReminderScheduler.should_send_early_reminder(material))

    def test_should_not_send_early_reminder_without_due_date(self):
        """Test early reminder not sent if no due date set."""
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment"
            # No due_date
        )

        self.assertFalse(ReminderScheduler.should_send_early_reminder(material))

    def test_should_not_send_early_reminder_when_too_far_away(self):
        """Test early reminder not sent when deadline is more than 48 hours away."""
        due_date = timezone.now() + timedelta(hours=60)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date
        )

        self.assertFalse(ReminderScheduler.should_send_early_reminder(material))

    def test_should_send_final_reminder_when_due_today(self):
        """Test final reminder should be sent when deadline is within 24 hours."""
        due_date = timezone.now() + timedelta(hours=12)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date
        )

        self.assertTrue(ReminderScheduler.should_send_final_reminder(material))

    def test_should_not_send_final_reminder_when_already_sent(self):
        """Test final reminder not sent if already marked as sent."""
        due_date = timezone.now() + timedelta(hours=12)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date,
            final_reminder_sent=True  # Already sent
        )

        self.assertFalse(ReminderScheduler.should_send_final_reminder(material))

    def test_should_not_send_final_reminder_when_far_away(self):
        """Test final reminder not sent when deadline is more than 24 hours away."""
        due_date = timezone.now() + timedelta(hours=48)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment 1",
            material_type="assignment",
            due_date=due_date
        )

        self.assertFalse(ReminderScheduler.should_send_final_reminder(material))


class AssignmentReminderSignalTests(TestCase):
    """Test the Django signal that triggers reminder sending."""

    def setUp(self):
        """Set up test data."""
        self.subject = Subject.objects.create(
            name="Mathematics",
            slug="mathematics"
        )

        self.teacher = User.objects.create_user(
            username="math_teacher",
            email="teacher@example.com",
            password="testpass123"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        self.course = Course.objects.create(
            title="Calculus 101",
            slug="calculus-101",
            teacher=self.teacher,
            description="Learn calculus",
            learning_objectives="Master calculus",
            price=149.99,
            max_students=25,
            subject=self.subject
        )

        # Create multiple enrolled students
        self.students = []
        for i in range(3):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="testpass123"
            )
            enrollment = Enrollment.objects.create(
                student=student,
                course=self.course,
                status="approved"
            )
            self.students.append(student)

    @patch('web.assignment_reminders.send_mail')
    def test_early_reminder_sent_on_assignment_creation(self, mock_send_mail):
        """Test that early reminder is sent when assignment created 36 hours before deadline."""
        due_date = timezone.now() + timedelta(hours=36)
        
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Homework 1",
            material_type="assignment",
            description="Chapter 1-3 exercises",
            due_date=due_date
        )

        # Check that an email was sent for each enrolled student
        self.assertEqual(mock_send_mail.call_count, len(self.students))

        # Check material was marked as reminder sent
        material.refresh_from_db()
        self.assertTrue(material.reminder_sent)

    @patch('web.assignment_reminders.send_mail')
    def test_final_reminder_sent_on_deadline_day(self, mock_send_mail):
        """Test final reminder sent when creating assignment due within 24 hours."""
        due_date = timezone.now() + timedelta(hours=6)
        
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Quiz",
            material_type="assignment",
            due_date=due_date
        )

        # Check that emails were sent
        self.assertGreater(mock_send_mail.call_count, 0)

        # Check material was marked as final reminder sent
        material.refresh_from_db()
        self.assertTrue(material.final_reminder_sent)

    @patch('web.assignment_reminders.send_mail')
    def test_no_reminder_for_non_assignment_materials(self, mock_send_mail):
        """Test that reminders are not sent for non-assignment materials."""
        due_date = timezone.now() + timedelta(hours=36)
        
        # Create a video material with a due date (unusual but possible)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Lecture Video",
            material_type="video",
            due_date=due_date
        )

        # No emails should be sent
        mock_send_mail.assert_not_called()

    @patch('web.assignment_reminders.send_mail')
    def test_no_reminder_for_unapproved_enrollments(self, mock_send_mail):
        """Test that reminders are not sent to unapproved enrollments."""
        # Create an unapproved enrollment
        pending_student = User.objects.create_user(
            username="pending",
            email="pending@example.com",
            password="testpass123"
        )
        Enrollment.objects.create(
            student=pending_student,
            course=self.course,
            status="pending"  # Not approved
        )

        due_date = timezone.now() + timedelta(hours=36)
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Assignment",
            material_type="assignment",
            due_date=due_date
        )

        # Only the 3 approved students should receive emails
        self.assertEqual(mock_send_mail.call_count, 3)

    @patch('web.assignment_reminders.send_mail')
    def test_reminder_email_contains_required_fields(self, mock_send_mail):
        """Test that reminder emails contain required information."""
        due_date = timezone.now() + timedelta(hours=36)
        
        CourseMaterial.objects.create(
            course=self.course,
            title="Test Assignment",
            material_type="assignment",
            description="Test this material",
            due_date=due_date
        )

        # Get the first call to send_mail
        call_args = mock_send_mail.call_args

        # Check that email contains assignment title
        email_body = call_args.kwargs.get('message') or call_args[0][1]
        self.assertIn('Test Assignment', email_body)


class CourseMaterialRemindeFlagTests(TestCase):
    """Test the reminder_sent and final_reminder_sent flags."""

    def setUp(self):
        """Set up test data."""
        self.subject = Subject.objects.create(
            name="Physics",
            slug="physics"
        )

        self.teacher = User.objects.create_user(
            username="professor",
            email="prof@example.com",
            password="testpass123"
        )
        self.teacher.profile.is_teacher = True
        self.teacher.profile.save()

        self.course = Course.objects.create(
            title="Physics 101",
            slug="physics-101",
            teacher=self.teacher,
            description="Learn physics",
            learning_objectives="Understand physics laws",
            price=199.99,
            max_students=40,
            subject=self.subject
        )

    def test_reminder_flags_start_as_false(self):
        """Test that reminder flags are False by default."""
        due_date = timezone.now() + timedelta(days=7)
        
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Lab Report",
            material_type="assignment",
            due_date=due_date
        )

        self.assertFalse(material.reminder_sent)
        self.assertFalse(material.final_reminder_sent)

    def test_reminder_flags_can_be_set_manually(self):
        """Test that reminder flags can be manually set."""
        due_date = timezone.now() + timedelta(days=7)
        
        material = CourseMaterial.objects.create(
            course=self.course,
            title="Lab Report",
            material_type="assignment",
            due_date=due_date,
            reminder_sent=True,
            final_reminder_sent=True
        )

        self.assertTrue(material.reminder_sent)
        self.assertTrue(material.final_reminder_sent)

    def test_reminder_flag_updates_after_sending(self):
        """Test that reminder flag is updated after sending reminder."""
        due_date = timezone.now() + timedelta(hours=36)
        
        with patch('web.assignment_reminders.send_mail'):
            material = CourseMaterial.objects.create(
                course=self.course,
                title="Assignment",
                material_type="assignment",
                due_date=due_date
            )

            # After creation, should be marked as sent
            material.refresh_from_db()
            self.assertTrue(material.reminder_sent)
