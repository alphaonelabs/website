from django.contrib.auth.models import User
from django.test import TestCase

from web.models import Profile


class NotificationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})


class RecommendationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})


class CalendarSyncTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})


class ForumTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@example.com", password="teacherpass123"
        )
        self.student = User.objects.create_user(
            username="student", email="student@example.com", password="studentpass123"
        )
        self.teacher_profile, _ = Profile.objects.get_or_create(user=self.teacher, defaults={"is_teacher": True})
        self.student_profile, _ = Profile.objects.get_or_create(user=self.student, defaults={"is_teacher": False})
