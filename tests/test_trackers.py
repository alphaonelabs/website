from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from web.models import ProgressTracker


class ProgressTrackerTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpassword")
        self.client.login(username="testuser", password="testpassword")
        self.tracker = ProgressTracker.objects.create(
            user=self.user,
            title="Test Tracker",
            description="Testing progress",
            current_value=25,
            target_value=100,
            color="blue-600",
            public=True,
        )

    def test_tracker_list(self):
        response = self.client.get(reverse("tracker_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")

    def test_create_tracker(self):
        """response = self.client.post(reverse('create_tracker'), {
            'title': 'New Tracker',
            'description': 'New description',
            'current_value': 10,
            'target_value': 50,
            'color': 'green-600',
            'public': True
        })"""
        self.assertEqual(ProgressTracker.objects.count(), 2)
        new_tracker = ProgressTracker.objects.get(title="New Tracker")
        self.assertEqual(new_tracker.current_value, 10)
        self.assertEqual(new_tracker.percentage, 20)

    def test_update_progress(self):
        response = self.client.post(
            reverse("update_progress", args=[self.tracker.id]),
            {"current_value": 50},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.tracker.refresh_from_db()
        self.assertEqual(self.tracker.current_value, 50)
        self.assertEqual(self.tracker.percentage, 50)

    def test_embed_tracker(self):
        response = self.client.get(reverse("embed_tracker", args=[self.tracker.embed_code]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Tracker")
        self.assertContains(response, "25%")


class SubjectStrengthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="analyticsuser", email="analytics@test.com", password="testpassword")
        self.client.login(username="analyticsuser", password="testpassword")

        from web.models import Subject, SubjectStrength

        self.subject = Subject.objects.create(name="Mathematics", slug="mathematics")
        self.strength = SubjectStrength.objects.create(
            user=self.user,
            subject=self.subject,
            strength_score=50.0,
            total_quizzes=0,
            total_correct=0,
            total_questions=0,
        )

    def test_initial_strength_score(self):
        self.assertEqual(self.strength.strength_score, 50.0)

    def test_update_from_quiz_first_attempt(self):
        self.strength.update_from_quiz(8, 10)
        self.strength.refresh_from_db()
        self.assertEqual(self.strength.strength_score, 80.0)
        self.assertEqual(self.strength.total_quizzes, 1)
        self.assertEqual(self.strength.total_correct, 8)
        self.assertEqual(self.strength.total_questions, 10)

    def test_update_from_quiz_weighted_average(self):
        self.strength.update_from_quiz(8, 10)  # Sets to 80
        self.strength.refresh_from_db()
        self.strength.update_from_quiz(6, 10)  # 70% of 80 + 30% of 60 = 56 + 18 = 74
        self.strength.refresh_from_db()
        self.assertAlmostEqual(self.strength.strength_score, 74.0, places=1)
        self.assertEqual(self.strength.total_quizzes, 2)

    def test_update_from_quiz_zero_max_score(self):
        original_score = self.strength.strength_score
        self.strength.update_from_quiz(0, 0)
        self.strength.refresh_from_db()
        self.assertEqual(self.strength.strength_score, original_score)
        self.assertEqual(self.strength.total_quizzes, 0)

    def test_unique_together_constraint(self):
        from django.db import IntegrityError

        from web.models import SubjectStrength

        with self.assertRaises(IntegrityError):
            SubjectStrength.objects.create(
                user=self.user,
                subject=self.subject,
                strength_score=60.0,
            )


class LearningAnalyticsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="learner", email="learner@test.com", password="testpassword")
        self.client.login(username="learner", password="testpassword")

    def test_analytics_dashboard_loads(self):
        response = self.client.get(reverse("learning_analytics"))
        self.assertEqual(response.status_code, 200)

    def test_analytics_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("learning_analytics"))
        self.assertEqual(response.status_code, 302)

    def test_analytics_with_no_data(self):
        from web.recommendations import get_learning_analytics

        analytics = get_learning_analytics(self.user)
        self.assertEqual(analytics["quiz_performance"]["total_attempts"], 0)
        self.assertEqual(analytics["quiz_performance"]["avg_score"], 0)
        self.assertEqual(analytics["attendance_rate"], 0)
        self.assertEqual(analytics["learning_velocity"], 0.0)
        self.assertEqual(analytics["total_study_hours"], 0.0)
        self.assertIsInstance(analytics["recommendations"], list)
        self.assertTrue(len(analytics["recommendations"]) > 0)

    def test_analytics_context_keys(self):
        from web.recommendations import get_learning_analytics

        analytics = get_learning_analytics(self.user)
        expected_keys = [
            "strengths",
            "weaknesses",
            "quiz_performance",
            "attendance_rate",
            "attendance_detail",
            "learning_velocity",
            "predicted_completion",
            "weekly_activity",
            "risk_courses",
            "recommendations",
            "subject_breakdown",
            "total_study_hours",
            "ai_coaching",
            "ai_study_tips",
            "learning_style_hint",
            "motivation_message",
        ]
        for key in expected_keys:
            self.assertIn(key, analytics)

    def test_analytics_quiz_trend(self):
        from web.recommendations import get_learning_analytics

        analytics = get_learning_analytics(self.user)
        self.assertIn("trend", analytics["quiz_performance"])
        self.assertIn("recent_avg", analytics["quiz_performance"])
        self.assertIn(analytics["quiz_performance"]["trend"], ["stable", "improving", "declining"])


class StudyPlanTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="planner", email="planner@test.com", password="testpassword")
        self.client.login(username="planner", password="testpassword")

    def test_study_plan_view_loads(self):
        response = self.client.get(reverse("study_plan"))
        self.assertEqual(response.status_code, 200)

    def test_study_plan_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("study_plan"))
        self.assertEqual(response.status_code, 302)

    def test_generate_study_plan(self):
        response = self.client.post(reverse("generate_study_plan"))
        self.assertEqual(response.status_code, 302)  # Redirects to study_plan

        from web.models import StudyPlan

        plan = StudyPlan.objects.filter(user=self.user, status="active").first()
        self.assertIsNotNone(plan)

    def test_regenerate_pauses_old_plan(self):
        from web.models import StudyPlan

        # Generate first plan
        self.client.post(reverse("generate_study_plan"))
        first_plan = StudyPlan.objects.filter(user=self.user, status="active").first()
        self.assertIsNotNone(first_plan)

        # Generate second plan
        self.client.post(reverse("generate_study_plan"))
        first_plan.refresh_from_db()
        self.assertEqual(first_plan.status, "paused")

        active_plans = StudyPlan.objects.filter(user=self.user, status="active")
        self.assertEqual(active_plans.count(), 1)

    def test_complete_study_plan_item(self):
        from web.models import StudyPlan, StudyPlanItem

        plan = StudyPlan.objects.create(user=self.user, title="Test Plan")
        item = StudyPlanItem.objects.create(
            plan=plan,
            item_type="review",
            title="Review Math",
            priority="high",
            order=1,
        )
        response = self.client.post(
            reverse("complete_study_plan_item", args=[item.id]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_completed)
        self.assertIsNotNone(item.completed_at)

    def test_complete_item_wrong_user(self):
        from web.models import StudyPlan, StudyPlanItem

        other_user = User.objects.create_user(username="other", email="other@test.com", password="testpassword")
        plan = StudyPlan.objects.create(user=other_user, title="Other Plan")
        item = StudyPlanItem.objects.create(
            plan=plan,
            item_type="review",
            title="Other Review",
            priority="medium",
            order=1,
        )
        response = self.client.post(
            reverse("complete_study_plan_item", args=[item.id]),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_plan_completion_percentage(self):
        from web.models import StudyPlan, StudyPlanItem

        plan = StudyPlan.objects.create(user=self.user, title="Test Plan")
        item1 = StudyPlanItem.objects.create(plan=plan, title="Item 1", order=1)
        StudyPlanItem.objects.create(plan=plan, title="Item 2", order=2)
        self.assertEqual(plan.completion_percentage, 0)

        item1.mark_complete()
        self.assertEqual(plan.completion_percentage, 50)


class SubjectStrengthSignalTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="signaluser", email="signal@test.com", password="testpassword")

        from web.models import Quiz, Subject

        self.subject = Subject.objects.create(name="Physics", slug="physics")
        self.quiz = Quiz.objects.create(
            title="Physics Quiz",
            subject=self.subject,
            status="published",
            creator=self.user,
        )

    def test_signal_creates_strength_on_first_quiz(self):
        from web.models import SubjectStrength, UserQuiz

        UserQuiz.objects.create(
            user=self.user,
            quiz=self.quiz,
            score=7,
            max_score=10,
            completed=True,
        )
        strength = SubjectStrength.objects.filter(user=self.user, subject=self.subject).first()
        self.assertIsNotNone(strength)
        self.assertAlmostEqual(strength.strength_score, 70.0, places=1)
        self.assertEqual(strength.total_quizzes, 1)

    def test_signal_updates_strength_on_subsequent_quiz(self):
        from web.models import SubjectStrength, UserQuiz

        UserQuiz.objects.create(user=self.user, quiz=self.quiz, score=8, max_score=10, completed=True)
        UserQuiz.objects.create(user=self.user, quiz=self.quiz, score=6, max_score=10, completed=True)
        strength = SubjectStrength.objects.get(user=self.user, subject=self.subject)
        # First: 80, then weighted: 0.7*80 + 0.3*60 = 56+18 = 74
        self.assertAlmostEqual(strength.strength_score, 74.0, places=1)
        self.assertEqual(strength.total_quizzes, 2)

    def test_signal_ignores_incomplete_quiz(self):
        from web.models import SubjectStrength, UserQuiz

        UserQuiz.objects.create(user=self.user, quiz=self.quiz, score=5, max_score=10, completed=False)
        self.assertFalse(SubjectStrength.objects.filter(user=self.user, subject=self.subject).exists())

    def test_signal_ignores_anonymous_quiz(self):
        from web.models import SubjectStrength, UserQuiz

        UserQuiz.objects.create(user=None, quiz=self.quiz, score=5, max_score=10, completed=True, anonymous_id="abc123")
        self.assertFalse(SubjectStrength.objects.filter(subject=self.subject).exists())
