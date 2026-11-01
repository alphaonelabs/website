from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from web.models import Course, StudyGroup, Subject


class StudyGroupInviteTests(TestCase):
    def setUp(self):
        # Create two users: user1 will be the teacher/creator, user2 will be invited.
        self.user1 = User.objects.create_user(username="user1", email="user1@example.com", password="pass")
        self.user2 = User.objects.create_user(username="user2", email="user2@example.com", password="pass")

        # Create a Subject instance (required by Course).
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")

        # Create a Course instance with all required fields.
        self.course = Course.objects.create(
            title="Test Course",
            slug="test-course",
            teacher=self.user1,  # Must supply a teacher
            description="Test course description",
            learning_objectives="Test learning objectives",
            prerequisites="",  # Optional field
            price=10.00,
            allow_individual_sessions=False,
            invite_only=False,
            status="published",
            max_students=50,  # Provide a valid number
            subject=self.subject,
            level="beginner",
            tags="",
            is_featured=False,
        )

        # Create a StudyGroup using the above Course.
        self.group = StudyGroup.objects.create(
            name="Test Group",
            description="Test group description",
            course=self.course,
            creator=self.user1,
            max_members=2,  # Limit group size for testing purposes
        )
        self.group.members.add(self.user1)
        self.client.login(username="user1", password="pass")

    @patch("web.views.Notification.objects.create")
    def test_invite_user_already_member(self, mock_notification_create):
        # Add user2 as a member first.
        self.group.members.add(self.user2)
        # Use follow=True so that we get the final response after redirect.
        response = self.client.post(
            reverse("invite_to_study_group", args=[self.group.id]), {"email_or_username": "user2"}, follow=True
        )
        self.assertContains(response, "is already a member of this group.")
