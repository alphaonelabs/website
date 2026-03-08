"""
Tests for learning views (HTTP-level)
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from learning.models import (
    Course,
    Lesson,
    LearnerProfile,
    LearningSession,
    Message,
    Progress,
    Topic,
)


class BaseViewTest(TestCase):
    """Common fixtures for view tests."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="viewer", password="viewpass")
        self.profile = LearnerProfile.objects.create(user=self.user)
        self.topic = Topic.objects.create(
            name="Python", description="Learn Python", difficulty="beginner", icon="🐍"
        )
        self.course = Course.objects.create(
            title="Python 101",
            description="Basics",
            topic=self.topic,
            difficulty="beginner",
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Variables",
            content="A variable stores a value.",
            lesson_type="theory",
            order=1,
            xp_reward=10,
        )

    def login(self):
        self.client.login(username="viewer", password="viewpass")


class HomeViewTest(BaseViewTest):
    def test_home_redirects_authenticated_user(self):
        self.login()
        resp = self.client.get(reverse("home"))
        self.assertRedirects(resp, reverse("dashboard"))

    def test_home_renders_for_anonymous(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "LearnPilot")


class DashboardViewTest(BaseViewTest):
    def test_dashboard_requires_login(self):
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 302)

    def test_dashboard_renders_for_logged_in_user(self):
        self.login()
        resp = self.client.get(reverse("dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "viewer")


class CourseListViewTest(BaseViewTest):
    def test_course_list_renders(self):
        self.login()
        resp = self.client.get(reverse("course_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Python 101")

    def test_course_list_filters_by_topic(self):
        self.login()
        resp = self.client.get(reverse("course_list") + f"?topic={self.topic.pk}")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Python 101")


class CourseDetailViewTest(BaseViewTest):
    def test_course_detail_renders(self):
        self.login()
        resp = self.client.get(reverse("course_detail", args=[self.course.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Variables")


class StartSessionViewTest(BaseViewTest):
    @patch("learning.views.get_tutor")
    def test_start_session_creates_session(self, mock_get_tutor):
        mock_tutor = MagicMock()
        mock_tutor.explain_concept.return_value = "Welcome to the lesson!"
        mock_get_tutor.return_value = mock_tutor

        self.login()
        resp = self.client.get(reverse("start_session", args=[self.lesson.pk]))

        # Should redirect to session
        self.assertEqual(resp.status_code, 302)
        session = LearningSession.objects.filter(learner=self.profile, lesson=self.lesson).first()
        self.assertIsNotNone(session)

    @patch("learning.views.get_tutor")
    def test_start_session_reuses_active_session(self, mock_get_tutor):
        mock_tutor = MagicMock()
        mock_tutor.explain_concept.return_value = "Welcome to the lesson!"
        mock_get_tutor.return_value = mock_tutor

        self.login()
        # First request – creates a session
        self.client.get(reverse("start_session", args=[self.lesson.pk]))
        count_after_first = LearningSession.objects.filter(learner=self.profile, lesson=self.lesson).count()

        # Second request – should reuse
        self.client.get(reverse("start_session", args=[self.lesson.pk]))
        count_after_second = LearningSession.objects.filter(learner=self.profile, lesson=self.lesson).count()

        self.assertEqual(count_after_first, count_after_second)


class TutorChatApiTest(BaseViewTest):
    def _make_session(self):
        return LearningSession.objects.create(learner=self.profile, lesson=self.lesson)

    @patch("learning.views.get_tutor")
    def test_chat_api_returns_response(self, mock_get_tutor):
        mock_tutor = MagicMock()
        mock_tutor.continue_conversation.return_value = "Great question!"
        mock_get_tutor.return_value = mock_tutor

        self.login()
        session = self._make_session()

        resp = self.client.post(
            reverse("tutor_chat_api", args=[session.pk]),
            data=json.dumps({"message": "What is a variable?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["response"], "Great question!")

    def test_chat_api_requires_post(self):
        self.login()
        session = self._make_session()
        resp = self.client.get(reverse("tutor_chat_api", args=[session.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_chat_api_rejects_empty_message(self):
        self.login()
        session = self._make_session()
        resp = self.client.post(
            reverse("tutor_chat_api", args=[session.pk]),
            data=json.dumps({"message": "   "}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class EvaluateAnswerApiTest(BaseViewTest):
    @patch("learning.views.get_tutor")
    def test_evaluate_returns_score(self, mock_get_tutor):
        mock_tutor = MagicMock()
        mock_tutor.evaluate_answer.return_value = {
            "score": 0.9,
            "feedback": "Excellent!",
            "correct_answer": "A named storage.",
        }
        mock_get_tutor.return_value = mock_tutor

        self.login()
        resp = self.client.post(
            reverse("evaluate_answer_api"),
            data=json.dumps(
                {
                    "question": "What is a variable?",
                    "answer": "A container for data.",
                    "lesson_id": self.lesson.pk,
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertAlmostEqual(float(data["score"]), 0.9)

    def test_evaluate_rejects_missing_fields(self):
        self.login()
        resp = self.client.post(
            reverse("evaluate_answer_api"),
            data=json.dumps({"question": "What is X?"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)


class ProgressViewTest(BaseViewTest):
    def test_progress_renders(self):
        self.login()
        resp = self.client.get(reverse("progress"))
        self.assertEqual(resp.status_code, 200)

    def test_progress_shows_completed_lessons(self):
        prog = Progress.objects.create(
            learner=self.profile, lesson=self.lesson, score=0.85, completed=True
        )
        self.login()
        resp = self.client.get(reverse("progress"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Variables")
