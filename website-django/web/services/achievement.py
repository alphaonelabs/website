from web.models import Achievement, CourseProgress, Enrollment, LearningStreak


def award_completion_badge(user, course):
    """
    Award a 'Course Completion' badge if the user's progress in the course is 100%.
    """
    try:
        enrollment = Enrollment.objects.get(student=user, course=course)
    except Enrollment.DoesNotExist:
        return

    progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
    # Check if the course has any sessions
    if course.sessions.count() == 0:
        return

    # completion_percentage is calculated as (completed_sessions / total_sessions) * 100
    if progress.completion_percentage == 100:
        if not Achievement.objects.filter(student=user, course=course, achievement_type="completion").exists():
            Achievement.objects.create(
                student=user,
                course=course,
                achievement_type="completion",
                title="Course Completed!",
                description=f"Congratulations! You have completed the course '{course.title}'.",
                badge_icon="fas fa-graduation-cap",
                criteria_threshold=100,
            )


def award_high_quiz_score_badge(user, quiz, score):
    """
    Award a 'High Quiz Score' badge if the user's quiz score meets a threshold.
    Assumes the quiz object has a 'title' attribute.
    """
    threshold = 90
    if score >= threshold:
        if not hasattr(quiz, "title"):
            raise ValueError("Quiz object must have a 'title' attribute")
        if not Achievement.objects.filter(student=user, achievement_type="quiz", title="High Quiz Score!").exists():
            Achievement.objects.create(
                student=user,
                course=None,
                achievement_type="quiz",
                title="High Quiz Score!",
                description=f"You scored {score}% on the quiz '{quiz.title}'. Great job!",
                badge_icon="fas fa-medal",
                criteria_threshold=threshold,
            )


def award_streak_badge(user):
    """
    Award a 'Daily Learning Streak' badge when the user's streak reaches specific thresholds.
    For example, a badge at 7 days and another at 30 days.
    """
    try:
        streak = user.learning_streak
    except LearningStreak.DoesNotExist:
        return

    if streak.current_streak >= 30:
        if not Achievement.objects.filter(
            student=user, achievement_type="streak", title="30-Day Learning Streak"
        ).exists():
            Achievement.objects.create(
                student=user,
                course=None,
                achievement_type="streak",
                title="30-Day Learning Streak",
                description="Amazing! You've maintained a 30-day learning streak.",
                badge_icon="fas fa-fire",
                criteria_threshold=30,
            )
    elif streak.current_streak >= 7:
        if not Achievement.objects.filter(
            student=user, achievement_type="streak", title="7-Day Learning Streak"
        ).exists():
            Achievement.objects.create(
                student=user,
                course=None,
                achievement_type="streak",
                title="7-Day Learning Streak",
                description="Great work! You've maintained a 7-day learning streak.",
                badge_icon="fas fa-fire",
                criteria_threshold=7,
            )
