"""URL configuration for the learning app."""

from django.urls import path

from . import views

urlpatterns = [
    # Home
    path("", views.HomeView.as_view(), name="home"),
    # Dashboard
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Courses
    path("courses/", views.CourseListView.as_view(), name="course_list"),
    path("courses/<int:pk>/", views.CourseDetailView.as_view(), name="course_detail"),
    # Adaptive path
    path("topics/<int:topic_id>/generate-path/", views.generate_path_view, name="generate_path"),
    path("paths/<int:pk>/", views.AdaptivePathDetailView.as_view(), name="adaptive_path_detail"),
    # Tutoring sessions
    path("lessons/<int:lesson_id>/start/", views.start_session_view, name="start_session"),
    path("sessions/<int:session_id>/", views.TutorSessionView.as_view(), name="tutor_session"),
    path("sessions/<int:session_id>/chat/", views.tutor_chat_api, name="tutor_chat_api"),
    path("sessions/<int:session_id>/end/", views.end_session_view, name="end_session"),
    # Practice & feedback
    path("lessons/<int:lesson_id>/practice/", views.practice_question_api, name="practice_question_api"),
    path("evaluate/", views.evaluate_answer_api, name="evaluate_answer_api"),
    # Progress
    path("progress/", views.ProgressView.as_view(), name="progress"),
]
