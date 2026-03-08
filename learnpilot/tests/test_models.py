"""
Tests for learning models
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from learning.models import (
    Course,
    Lesson,
    LearnerProfile,
    LearningSession,
    Message,
    Progress,
    Topic,
)


class TopicModelTest(TestCase):
    def test_str(self):
        topic = Topic(name="Python", description="", difficulty="beginner", icon="🐍")
        self.assertEqual(str(topic), "Python")


class CourseModelTest(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(
            name="Python", description="Learn Python", difficulty="beginner", icon="🐍"
        )
        self.course = Course.objects.create(
            title="Python Fundamentals",
            description="Core Python",
            topic=self.topic,
            difficulty="beginner",
            estimated_hours=4.0,
        )

    def test_str(self):
        self.assertIn("Python Fundamentals", str(self.course))

    def test_total_lessons(self):
        self.assertEqual(self.course.total_lessons(), 0)
        Lesson.objects.create(
            course=self.course, title="Variables", content="Variables", lesson_type="theory", order=1
        )
        self.assertEqual(self.course.total_lessons(), 1)


class LearnerProfileTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="pass")
        self.profile = LearnerProfile.objects.create(user=self.user)

    def test_str(self):
        self.assertIn("testuser", str(self.profile))

    def test_update_activity_initialises_streak(self):
        self.profile.streak_days = 0
        self.profile.last_active = None
        self.profile.save()
        self.profile.update_activity()
        self.assertEqual(self.profile.streak_days, 1)

    def test_update_activity_increments_streak(self):
        yesterday = timezone.now() - timezone.timedelta(days=1)
        self.profile.last_active = yesterday
        self.profile.streak_days = 3
        self.profile.save()
        self.profile.update_activity()
        self.assertEqual(self.profile.streak_days, 4)

    def test_update_activity_resets_streak_on_gap(self):
        old_date = timezone.now() - timezone.timedelta(days=3)
        self.profile.last_active = old_date
        self.profile.streak_days = 10
        self.profile.save()
        self.profile.update_activity()
        self.assertEqual(self.profile.streak_days, 1)


class ProgressModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="pass")
        self.profile = LearnerProfile.objects.create(user=self.user)
        self.topic = Topic.objects.create(
            name="Python", description="", difficulty="beginner", icon="🐍"
        )
        self.course = Course.objects.create(
            title="Basics", description="", topic=self.topic, difficulty="beginner"
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Variables",
            content="Vars",
            lesson_type="theory",
            order=1,
            xp_reward=20,
        )

    def test_mark_complete_awards_xp(self):
        prog = Progress.objects.create(learner=self.profile, lesson=self.lesson)
        self.profile.total_xp = 0
        self.profile.save()

        prog.mark_complete(score=0.9)

        prog.refresh_from_db()
        self.assertTrue(prog.completed)
        self.assertAlmostEqual(prog.score, 0.9)
        self.assertIsNotNone(prog.completed_at)

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_xp, 20)

    def test_mark_complete_clamps_score(self):
        prog = Progress.objects.create(learner=self.profile, lesson=self.lesson)
        prog.mark_complete(score=1.5)
        prog.refresh_from_db()
        self.assertEqual(prog.score, 1.0)


class LearningSessionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="sess_user", password="pass")
        self.profile = LearnerProfile.objects.create(user=self.user)
        self.topic = Topic.objects.create(
            name="Web", description="", difficulty="intermediate", icon="🌐"
        )
        self.course = Course.objects.create(
            title="HTML", description="", topic=self.topic, difficulty="beginner"
        )
        self.lesson = Lesson.objects.create(
            course=self.course,
            title="Intro",
            content="HTML intro",
            lesson_type="theory",
            order=1,
        )

    def test_end_session(self):
        session = LearningSession.objects.create(learner=self.profile, lesson=self.lesson)
        self.assertTrue(session.is_active)
        session.end_session()
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertIsNotNone(session.ended_at)

    def test_duration_seconds_when_active(self):
        session = LearningSession.objects.create(learner=self.profile, lesson=self.lesson)
        duration = session.duration_seconds()
        self.assertGreaterEqual(duration, 0)

    def test_message_creation(self):
        session = LearningSession.objects.create(learner=self.profile, lesson=self.lesson)
        msg = Message.objects.create(session=session, role="user", content="Hello")
        self.assertIn("Hello", str(msg))
