# web/tests/test_achievements.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from web.models import Achievement, Course, CourseProgress, Enrollment, LearningStreak, Session, Subject
from web.services.achievement import award_completion_badge, award_high_quiz_score_badge, award_streak_badge

User = get_user_model()


class AchievementTests(TestCase):
    def setUp(self):
        # Create a test user.
        self.user = User.objects.create_user(username="testuser", password="pass")
        # Create a subject (required for Course).
        self.subject = Subject.objects.create(name="Test Subject", slug="test-subject")
        # Create a course with the subject.
        self.course = Course.objects.create(
            title="Test Course", teacher=self.user, price=0, max_students=10, subject=self.subject, level="beginner"
        )
        # Create an enrollment and mark it as completed.
        self.enrollment = Enrollment.objects.create(student=self.user, course=self.course, status="completed")
        self.progress, _ = CourseProgress.objects.get_or_create(enrollment=self.enrollment)
        # Create a session and mark it as completed to simulate full course progress.
        self.session = Session.objects.create(
            course=self.course,
            title="Test Session",
            description="A test session.",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
            is_virtual=True,
        )
        self.progress.completed_sessions.add(self.session)

    def test_award_completion_badge(self):
        self.assertFalse(
            Achievement.objects.filter(student=self.user, course=self.course, achievement_type="completion").exists()
        )
        award_completion_badge(self.user, self.course)
        achievement = Achievement.objects.filter(
            student=self.user, course=self.course, achievement_type="completion"
        ).first()
        self.assertIsNotNone(achievement)
        self.assertEqual(achievement.title, "Course Completed!")
        self.assertEqual(achievement.badge_icon, "fas fa-graduation-cap")
        self.assertEqual(achievement.criteria_threshold, 100)

    def test_award_high_quiz_score_badge(self):
        class DummyQuiz:
            title = "Test Quiz"

        quiz = DummyQuiz()
        award_high_quiz_score_badge(self.user, quiz, 95)
        achievement = Achievement.objects.filter(
            student=self.user, achievement_type="quiz", title="High Quiz Score!"
        ).first()
        self.assertIsNotNone(achievement)
        self.assertEqual(achievement.title, "High Quiz Score!")
        self.assertEqual(achievement.badge_icon, "fas fa-medal")
        self.assertEqual(achievement.criteria_threshold, 90)
        self.assertIsNone(achievement.course)

    def test_award_streak_badge(self):
        streak, _ = LearningStreak.objects.get_or_create(user=self.user)
        # Test 7-day streak.
        streak.current_streak = 7
        streak.save()
        award_streak_badge(self.user)
        achievement_7 = Achievement.objects.filter(
            student=self.user, achievement_type="streak", title="7-Day Learning Streak"
        ).first()
        self.assertIsNotNone(achievement_7)
        self.assertEqual(achievement_7.badge_icon, "fas fa-fire")
        self.assertEqual(achievement_7.criteria_threshold, 7)

        # Test 30-day streak.
        streak.current_streak = 30
        streak.save()
        award_streak_badge(self.user)
        achievement_30 = Achievement.objects.filter(
            student=self.user, achievement_type="streak", title="30-Day Learning Streak"
        ).first()
        self.assertIsNotNone(achievement_30)
        self.assertEqual(achievement_30.badge_icon, "fas fa-fire")
        self.assertEqual(achievement_30.criteria_threshold, 30)
