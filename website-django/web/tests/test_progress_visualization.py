import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from web.models import Course, CourseProgress, Enrollment, LearningStreak, Session, SessionAttendance, Subject


class ProgressVisualizationTest(TestCase):
    """Test cases for the progress_visualization view and its helper functions."""

    def setUp(self):
        """Set up test data for progress visualization tests."""
        # Create test user
        self.password = "testpassword123"
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
        )
        self.client = Client()
        self.client.login(username="testuser", password=self.password)

        # Create a subject first
        self.subject = Subject.objects.create(
            name="Programming",
            slug="programming",
        )

        # Create test courses
        self.course1 = Course.objects.create(
            title="Python Basics",
            description="Introduction to Python",
            learning_objectives="Learn Python basics",
            prerequisites="None",
            price=99.99,
            max_students=20,
            subject=self.subject,
            teacher=self.user,
            slug="python-basics",
        )
        self.course2 = Course.objects.create(
            title="Advanced Django",
            description="Advanced web development with Django",
            learning_objectives="Learn advanced Django concepts",
            prerequisites="Basic Django knowledge",
            price=149.99,
            max_students=15,
            subject=self.subject,
            teacher=self.user,
            slug="advanced-django",
        )

        # Create course sessions
        now = timezone.now()

        # Create sessions for course 1
        self.sessions_c1 = []
        for i in range(5):
            session = Session.objects.create(
                course=self.course1,
                title=f"Session {i + 1}",
                description=f"Description for session {i + 1}",
                start_time=now - timedelta(days=10 - i, hours=2),
                end_time=now - timedelta(days=10 - i),
            )
            self.sessions_c1.append(session)

        # Create sessions for course 2
        self.sessions_c2 = []
        for i in range(3):
            session = Session.objects.create(
                course=self.course2,
                title=f"Advanced Session {i + 1}",
                description=f"Advanced description for session {i + 1}",
                start_time=now - timedelta(days=5 - i, hours=2),
                end_time=now - timedelta(days=5 - i),
            )
            self.sessions_c2.append(session)

        # Create enrollments
        self.enrollment1 = Enrollment.objects.create(
            student=self.user,
            course=self.course1,
            enrollment_date=now - timedelta(days=15),
            status="approved",
        )

        self.enrollment2 = Enrollment.objects.create(
            student=self.user,
            course=self.course2,
            enrollment_date=now - timedelta(days=8),
            status="completed",
            completion_date=now - timedelta(days=1),
        )

        # Create progress records
        self.progress1 = CourseProgress.objects.create(enrollment=self.enrollment1)
        self.progress1.completed_sessions.add(self.sessions_c1[0], self.sessions_c1[1], self.sessions_c1[2])

        self.progress2 = CourseProgress.objects.create(enrollment=self.enrollment2)
        self.progress2.completed_sessions.add(*self.sessions_c2)

        # Create attendance records
        for session in self.sessions_c1[:3]:
            SessionAttendance.objects.create(
                student=self.user,
                session=session,
                status="present",
            )

        SessionAttendance.objects.create(
            student=self.user,
            session=self.sessions_c1[3],
            status="absent",
        )

        for session in self.sessions_c2:
            SessionAttendance.objects.create(
                student=self.user,
                session=session,
                status="present" if session != self.sessions_c2[1] else "late",
            )

        # Create learning streak record
        self.streak = LearningStreak.objects.create(user=self.user, current_streak=5)

    @patch("django.core.cache.cache.get")
    @patch("django.core.cache.cache.set")
    def test_progress_visualization_view(self, mock_cache_set, mock_cache_get):
        """Test that the progress visualization view returns correct data and uses cache appropriately."""
        # Set the mock to return None initially (cache miss)
        mock_cache_get.return_value = None

        url = reverse("progress_visualization")
        response = self.client.get(url)

        # Check basic response properties
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/progress_visualization.html")

        # Verify that cache was set
        self.assertTrue(mock_cache_set.called)
        mock_cache_set.assert_called_once()

        # Get call arguments (args and kwargs)
        call_args, call_kwargs = mock_cache_set.call_args
        self.assertEqual(call_args[0], f"user_progress_{self.user.id}")  # Cache key
        self.assertIsInstance(call_args[1], dict)  # Context is a dictionary
        self.assertIsNone(call_kwargs.get("timeout"))  # Timeout should be None in kwargs

        # Check context data calculations
        context = response.context

        # Course statistics
        self.assertEqual(context["total_courses"], 2)
        self.assertEqual(context["courses_completed"], 1)
        self.assertEqual(context["courses_completed_percentage"], 50)
        self.assertEqual(context["topics_mastered"], 6)

        # Attendance stats
        self.assertEqual(context["average_attendance"], 86)

        # Check that most_active_day is a valid day of the week
        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.assertIn(context["most_active_day"], days_of_week)

        # Check learning activity stats
        self.assertEqual(context["current_streak"], 5)
        self.assertIsInstance(context["total_learning_hours"], float)
        self.assertIsInstance(context["avg_sessions_per_week"], float)

        # Check completion pace
        self.assertIn("days/course", context["completion_pace"])

        # Course data
        self.assertEqual(len(context["courses"]), 2)

        # Check that JSON data is properly formatted
        try:
            parsed_dates = json.loads(context["progress_dates"])
            self.assertIsInstance(parsed_dates, list)

            parsed_sessions = json.loads(context["sessions_completed"])
            self.assertIsInstance(parsed_sessions, list)
            self.assertEqual(len(parsed_sessions), 2)

            parsed_courses = json.loads(context["courses_json"])
            self.assertIsInstance(parsed_courses, list)
            self.assertEqual(len(parsed_courses), 2)
        except json.JSONDecodeError:
            self.fail("JSON data in context is not properly formatted")

        # Test cache hit scenario
        mock_cache_get.reset_mock()
        mock_cache_set.reset_mock()
        # Convert ContextList to a plain dict for cache hit simulation
        context_dict = dict(context)
        mock_cache_get.return_value = context_dict
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(mock_cache_set.called)  # Cache should not be set again on hit

    def test_unauthenticated_access(self):
        """Test that unauthenticated users are redirected to login."""
        self.client.logout()
        url = reverse("progress_visualization")
        response = self.client.get(url)

        # Should redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/en/accounts/login/"))

    def test_calculate_course_stats(self):
        """Test the calculate_course_stats helper function."""
        from web.views import calculate_course_stats

        enrollments = Enrollment.objects.filter(student=self.user)
        stats = calculate_course_stats(enrollments)

        self.assertEqual(stats["total_courses"], 2)
        self.assertEqual(stats["courses_completed"], 1)
        self.assertEqual(stats["courses_completed_percentage"], 50)
        self.assertEqual(stats["topics_mastered"], 6)

    def test_calculate_attendance_stats(self):
        """Test the calculate_attendance_stats helper function."""
        from web.views import calculate_attendance_stats

        enrollments = Enrollment.objects.filter(student=self.user)
        stats = calculate_attendance_stats(self.user, enrollments)

        self.assertEqual(stats["average_attendance"], 86)

    def test_calculate_learning_activity(self):
        """Test the calculate_learning_activity helper function."""
        from web.views import calculate_learning_activity

        enrollments = Enrollment.objects.filter(student=self.user)
        stats = calculate_learning_activity(self.user, enrollments)

        self.assertEqual(stats["current_streak"], 5)
        self.assertIsInstance(stats["total_learning_hours"], float)
        self.assertIsInstance(stats["avg_sessions_per_week"], float)

        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        self.assertIn(stats["most_active_day"], days_of_week)

    def test_calculate_completion_pace(self):
        """Test the calculate_completion_pace helper function."""
        from web.views import calculate_completion_pace

        enrollments = Enrollment.objects.filter(student=self.user)
        stats = calculate_completion_pace(enrollments)

        self.assertIn("days/course", stats["completion_pace"])

    def test_get_all_completed_sessions(self):
        """Test the get_all_completed_sessions helper function."""
        from web.views import get_all_completed_sessions

        enrollments = Enrollment.objects.filter(student=self.user)
        sessions = get_all_completed_sessions(enrollments)

        self.assertEqual(len(sessions), 6)  # 3 from course1 + 3 from course2

    def test_prepare_chart_data(self):
        """Test the prepare_chart_data helper function."""
        from web.views import prepare_chart_data

        enrollments = Enrollment.objects.filter(student=self.user)
        chart_data = prepare_chart_data(enrollments)

        self.assertEqual(len(chart_data["courses"]), 2)
        self.assertIn("progress_dates", chart_data)
        self.assertIn("sessions_completed", chart_data)
        self.assertIn("courses_json", chart_data)
