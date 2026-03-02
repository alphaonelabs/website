from django.db.models import Avg, Count, Q

from .models import Course


def get_course_recommendations(user, limit=6):
    """
    Generate personalized course recommendations for a user based on:
    1. Previous enrollments (similar categories/tags)
    2. Course ratings and popularity
    3. User's profile interests
    """
    if not user.is_authenticated:
        # For anonymous users, return popular courses
        return get_popular_courses(limit)

    # Get user's enrolled courses
    enrolled_courses = Course.objects.filter(enrollments__student=user)

    # Get subjects and tags from user's enrolled courses
    subjects = enrolled_courses.values_list("subject", flat=True).distinct()
    tags = []
    for course in enrolled_courses:
        tags.extend([tag.strip() for tag in course.tags.split(",") if tag.strip()])
    tags = list(set(tags))  # Remove duplicates

    # Base queryset excluding enrolled courses
    recommendations = (
        Course.objects.exclude(enrollments__student=user)
        .filter(status="published")
        .annotate(avg_rating=Avg("reviews__rating"), enrollment_count=Count("enrollments"))
    )

    # If user has enrolled courses, prioritize similar courses
    if subjects or tags:
        subject_matches = Q(subject__in=subjects) if subjects else Q()
        tag_matches = Q()
        for tag in tags:
            tag_matches |= Q(tags__icontains=tag)

        recommendations = recommendations.filter(subject_matches | tag_matches)

    # Consider user's profile interests if available
    if hasattr(user, "profile") and user.profile.expertise:
        expertise_keywords = [kw.strip() for kw in user.profile.expertise.lower().split(",")]
        expertise_matches = Q()
        for keyword in expertise_keywords:
            expertise_matches |= (
                Q(title__icontains=keyword) | Q(description__icontains=keyword) | Q(tags__icontains=keyword)
            )
        recommendations = recommendations.filter(expertise_matches)

    # Order by a combination of factors
    recommendations = recommendations.order_by("-avg_rating", "-enrollment_count", "-created_at")

    return recommendations[:limit]


def get_popular_courses(limit=6):
    """Get popular courses based on enrollment count and ratings."""
    return (
        Course.objects.filter(status="published")
        .annotate(avg_rating=Avg("reviews__rating"), enrollment_count=Count("enrollments"))
        .order_by("-enrollment_count", "-avg_rating", "-created_at")[:limit]
    )


def get_similar_courses(course, limit=3):
    """Get courses similar to a given course."""
    similar_courses = Course.objects.filter(status="published").exclude(id=course.id)

    # Match by subject and tags
    tags = [tag.strip() for tag in course.tags.split(",") if tag.strip()]
    tag_matches = Q()
    for tag in tags:
        tag_matches |= Q(tags__icontains=tag)

    similar_courses = (
        similar_courses.filter(Q(subject=course.subject) | tag_matches)
        .annotate(avg_rating=Avg("reviews__rating"), enrollment_count=Count("enrollments"))
        .order_by("-avg_rating", "-enrollment_count")
    )

    return similar_courses[:limit]


def get_learning_analytics(user):
    """Return learning analytics data for the given user."""
    import json
    import logging
    from datetime import timedelta

    from django.db.models import Avg, Count, F, Sum
    from django.utils import timezone

    from .models import (
        CourseProgress,
        Enrollment,
        Session,
        SessionAttendance,
        SubjectStrength,
        UserQuiz,
    )

    logger = logging.getLogger(__name__)
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    ninety_days_ago = now - timedelta(days=90)

    # --- Quiz Performance (all time + recent trend) ---
    quiz_attempts = UserQuiz.objects.filter(user=user, completed=True)
    total_attempts = quiz_attempts.count()
    recent_attempts = quiz_attempts.filter(start_time__gte=thirty_days_ago)
    avg_score = 0
    recent_avg_score = 0
    score_trend = "stable"

    if total_attempts > 0:
        scores = []
        for attempt in quiz_attempts:
            if attempt.max_score > 0:
                scores.append((attempt.score / attempt.max_score) * 100)
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    if recent_attempts.exists():
        recent_scores = []
        for attempt in recent_attempts:
            if attempt.max_score > 0:
                recent_scores.append((attempt.score / attempt.max_score) * 100)
        recent_avg_score = round(sum(recent_scores) / len(recent_scores), 1) if recent_scores else 0
        if recent_avg_score > avg_score + 5:
            score_trend = "improving"
        elif recent_avg_score < avg_score - 5:
            score_trend = "declining"

    # --- Subject Breakdown ---
    subject_strengths = SubjectStrength.objects.filter(user=user).select_related("subject")
    strengths = []
    weaknesses = []
    subject_breakdown = []
    for ss in subject_strengths:
        entry = {
            "subject": ss.subject.name,
            "score": round(ss.strength_score, 1),
            "quizzes": ss.total_quizzes,
            "accuracy": round((ss.total_correct / ss.total_questions) * 100, 1) if ss.total_questions > 0 else 0,
        }
        subject_breakdown.append(entry)
        if ss.strength_score >= 70:
            strengths.append(entry)
        elif ss.strength_score < 50:
            weaknesses.append(entry)

    strengths.sort(key=lambda x: x["score"], reverse=True)
    weaknesses.sort(key=lambda x: x["score"])

    # --- Attendance ---
    total_attendances = SessionAttendance.objects.filter(student=user).count()
    attended = SessionAttendance.objects.filter(student=user, status__in=["present", "late"]).count()
    late_count = SessionAttendance.objects.filter(student=user, status="late").count()
    absent_count = SessionAttendance.objects.filter(student=user, status="absent").count()
    attendance_rate = round((attended / total_attendances) * 100, 1) if total_attendances > 0 else 0

    # --- Learning Velocity ---
    recent_attendances = SessionAttendance.objects.filter(
        student=user, created_at__gte=thirty_days_ago, status__in=["present", "late"]
    ).count()
    learning_velocity = round(recent_attendances / 4.3, 1)

    # --- Weekly Activity (last 8 weeks) ---
    weekly_activity = []
    for i in range(7, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end = now - timedelta(weeks=i)
        sessions_count = SessionAttendance.objects.filter(
            student=user, created_at__gte=week_start, created_at__lt=week_end, status__in=["present", "late"]
        ).count()
        quizzes_count = UserQuiz.objects.filter(
            user=user, completed=True, start_time__gte=week_start, start_time__lt=week_end
        ).count()
        weekly_activity.append(
            {
                "week": f"W{8 - i}",
                "sessions": sessions_count,
                "quizzes": quizzes_count,
                "total": sessions_count + quizzes_count,
            }
        )

    # --- Course Progress & Risk ---
    enrollments = Enrollment.objects.filter(student=user, status__in=["approved", "pending"]).select_related("course")
    predicted_completion = []
    risk_courses = []
    for enrollment in enrollments:
        try:
            progress = CourseProgress.objects.get(enrollment=enrollment)
            pct = progress.completion_percentage
        except CourseProgress.DoesNotExist:
            pct = 0

        total_sessions = enrollment.course.sessions.count()
        completed_sessions = 0
        if hasattr(enrollment, "progress"):
            try:
                completed_sessions = enrollment.progress.completed_sessions.count()
            except Exception:
                pass

        remaining = total_sessions - completed_sessions
        if learning_velocity > 0 and remaining > 0:
            weeks_remaining = remaining / learning_velocity
            predicted_date = (now + timedelta(weeks=weeks_remaining)).date()
        else:
            predicted_date = None

        course_info = {
            "course": enrollment.course.title,
            "progress": pct,
            "predicted_date": predicted_date,
            "remaining_sessions": remaining,
            "total_sessions": total_sessions,
        }
        predicted_completion.append(course_info)

        if pct < 30 and total_sessions > 0:
            risk_courses.append(course_info)

    total_study_hours = round(attended * 1.5, 1)

    # --- Build student profile for AI ---
    student_profile = {
        "name": user.get_full_name() or user.username,
        "quiz_avg": avg_score,
        "recent_quiz_avg": recent_avg_score,
        "score_trend": score_trend,
        "total_quizzes": total_attempts,
        "attendance_rate": attendance_rate,
        "late_count": late_count,
        "absent_count": absent_count,
        "learning_velocity": learning_velocity,
        "study_hours": total_study_hours,
        "strengths": [{"subject": s["subject"], "score": s["score"]} for s in strengths],
        "weaknesses": [{"subject": w["subject"], "score": w["score"]} for w in weaknesses],
        "risk_courses": [{"course": r["course"], "progress": r["progress"]} for r in risk_courses],
        "enrolled_courses": [{"course": p["course"], "progress": p["progress"]} for p in predicted_completion],
        "weekly_totals": [w["total"] for w in weekly_activity],
    }

    # --- Insights ---
    ai_insights = _generate_ai_insights(student_profile, logger)

    # --- Fallback recommendations (always available) ---
    recommendations = ai_insights.get("recommendations", [])
    if not recommendations:
        recommendations = _generate_fallback_recommendations(
            weaknesses, attendance_rate, learning_velocity, risk_courses, total_attempts, avg_score
        )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "quiz_performance": {
            "total_attempts": total_attempts,
            "avg_score": avg_score,
            "recent_avg": recent_avg_score,
            "trend": score_trend,
        },
        "attendance_rate": attendance_rate,
        "attendance_detail": {
            "total": total_attendances,
            "attended": attended,
            "late": late_count,
            "absent": absent_count,
        },
        "learning_velocity": learning_velocity,
        "predicted_completion": predicted_completion,
        "weekly_activity": weekly_activity,
        "risk_courses": risk_courses,
        "recommendations": recommendations,
        "subject_breakdown": subject_breakdown,
        "total_study_hours": total_study_hours,
        "ai_coaching": ai_insights.get("coaching_message", ""),
        "ai_study_tips": ai_insights.get("study_tips", []),
        "learning_style_hint": ai_insights.get("learning_style", ""),
        "motivation_message": ai_insights.get("motivation", ""),
    }


def _generate_ai_insights(student_profile, logger):
    """Call OpenAI for learning insights. Returns empty dict on failure."""
    import json

    from django.conf import settings

    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return {}

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)

        prompt = f"""You are an expert educational AI tutor analyzing a student's learning data.
Based on this student profile, provide personalized, actionable insights.

STUDENT DATA:
- Name: {student_profile['name']}
- Overall quiz average: {student_profile['quiz_avg']}%
- Recent 30-day quiz average: {student_profile['recent_quiz_avg']}%
- Score trend: {student_profile['score_trend']}
- Total quizzes completed: {student_profile['total_quizzes']}
- Attendance rate: {student_profile['attendance_rate']}%
- Late arrivals: {student_profile['late_count']}, Absences: {student_profile['absent_count']}
- Learning velocity: {student_profile['learning_velocity']} sessions/week
- Total study hours: {student_profile['study_hours']}
- Strong subjects: {json.dumps(student_profile['strengths'])}
- Weak subjects: {json.dumps(student_profile['weaknesses'])}
- At-risk courses: {json.dumps(student_profile['risk_courses'])}
- Enrolled courses: {json.dumps(student_profile['enrolled_courses'])}
- Weekly activity (last 8 weeks): {student_profile['weekly_totals']}

Respond with ONLY valid JSON (no markdown, no code blocks) in this exact format:
{{
  "coaching_message": "A warm, personalized 2-3 sentence coaching message addressing the student by name. Be encouraging but honest about areas to improve.",
  "recommendations": [
    {{"icon": "fas fa-icon-name", "text": "Specific actionable recommendation", "priority": "high|medium|low"}},
    {{"icon": "fas fa-icon-name", "text": "Another recommendation", "priority": "high|medium|low"}}
  ],
  "study_tips": [
    "Specific study tip based on their data",
    "Another personalized tip"
  ],
  "learning_style": "Brief observation about their apparent learning style based on the data patterns",
  "motivation": "A short motivational message tailored to their current situation"
}}

Rules:
- Give 3-5 recommendations, prioritized by urgency
- Make study_tips specific to their weak subjects and situation (give 3-4)
- If they have no data yet, be welcoming and suggest getting started
- Use Font Awesome icon names (fas fa-...) for recommendation icons
- Be specific — reference actual subject names, course names, and numbers from their data
- If attendance is low, address it. If scores are declining, address it.
- For a student doing well, suggest stretch goals and peer mentoring"""

        model = getattr(settings, "AI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=800,
        )

        raw = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        if raw.startswith("json"):
            raw = raw[4:]

        return json.loads(raw.strip())

    except Exception as e:
        logger.warning(f"AI insights generation failed: {e}")
        return {}


def _generate_fallback_recommendations(weaknesses, attendance_rate, learning_velocity, risk_courses, total_attempts, avg_score):
    """Rule-based recommendations fallback."""
    recommendations = []
    if weaknesses:
        weak_names = ", ".join([w["subject"] for w in weaknesses[:3]])
        recommendations.append(
            {"icon": "fas fa-bullseye", "text": f"Focus on improving: {weak_names}", "priority": "high"}
        )
    if attendance_rate < 80:
        recommendations.append(
            {
                "icon": "fas fa-calendar-check",
                "text": f"Your attendance is {attendance_rate}%. Try to attend more sessions consistently.",
                "priority": "high",
            }
        )
    if learning_velocity < 2:
        recommendations.append(
            {"icon": "fas fa-tachometer-alt", "text": "Increase your weekly study sessions to build momentum.", "priority": "medium"}
        )
    if risk_courses:
        for rc in risk_courses[:2]:
            recommendations.append(
                {
                    "icon": "fas fa-exclamation-triangle",
                    "text": f"'{rc['course']}' is at risk ({rc['progress']}% complete). Prioritize it.",
                    "priority": "high",
                }
            )
    if total_attempts > 5 and avg_score > 80:
        recommendations.append(
            {
                "icon": "fas fa-star",
                "text": "Great quiz performance! Consider helping peers or exploring advanced topics.",
                "priority": "low",
            }
        )
    if not recommendations:
        recommendations.append(
            {"icon": "fas fa-thumbs-up", "text": "You're on track! Keep up the consistent effort.", "priority": "low"}
        )
    return recommendations


def generate_study_plan(user):
    """Generate a study plan for the user based on their analytics data."""
    import json
    import logging
    from datetime import timedelta

    from django.conf import settings
    from django.utils import timezone

    from .models import (
        Enrollment,
        Quiz,
        Session,
        StudyPlan,
        StudyPlanItem,
        SubjectStrength,
    )

    logger = logging.getLogger(__name__)
    now = timezone.now()

    # Deactivate old plans
    StudyPlan.objects.filter(user=user, status="active").update(status="paused")

    analytics = get_learning_analytics(user)

    # Gather context for AI
    enrollments = Enrollment.objects.filter(student=user, status__in=["approved", "pending"]).select_related("course")
    upcoming_sessions = Session.objects.filter(
        course__enrollments__in=enrollments, start_time__gt=now, start_time__lte=now + timedelta(days=14)
    ).order_by("start_time").select_related("course")[:15]

    weak_subjects = SubjectStrength.objects.filter(user=user, strength_score__lt=50).select_related("subject")
    medium_subjects = SubjectStrength.objects.filter(
        user=user, strength_score__gte=50, strength_score__lt=70
    ).select_related("subject")

    available_quizzes = []
    for ss in list(weak_subjects) + list(medium_subjects):
        quizzes = Quiz.objects.filter(subject=ss.subject, status="published")[:2]
        for q in quizzes:
            available_quizzes.append({"id": q.id, "title": q.title, "subject": ss.subject.name})

    session_list = []
    for s in upcoming_sessions:
        session_list.append({
            "id": s.id,
            "title": s.title,
            "course": s.course.title,
            "date": s.start_time.strftime("%Y-%m-%d %H:%M"),
        })

    # Try plan generation via OpenAI
    ai_plan_items = _generate_ai_study_plan(
        analytics, session_list, available_quizzes,
        [{"subject": ss.subject.name, "score": ss.strength_score} for ss in weak_subjects],
        [{"subject": ss.subject.name, "score": ss.strength_score} for ss in medium_subjects],
        user.get_full_name() or user.username,
        logger,
    )

    plan = StudyPlan.objects.create(
        user=user,
        title=f"Study Plan — {now.strftime('%B %d, %Y')}",
        description=ai_plan_items.get("plan_description", "Plan based on your learning analytics."),
        daily_goal_minutes=ai_plan_items.get("daily_goal_minutes", 30),
        weekly_goal_sessions=ai_plan_items.get("weekly_goal_sessions", 5),
    )

    items = ai_plan_items.get("items", [])
    if not items:
        # Fallback to rule-based generation
        items = _generate_fallback_plan_items(
            upcoming_sessions, weak_subjects, medium_subjects, available_quizzes, analytics
        )

    # Create StudyPlanItem objects
    session_map = {s.id: s for s in upcoming_sessions}
    quiz_map = {q["id"]: q for q in available_quizzes}
    course_map = {}
    for enrollment in enrollments:
        course_map[enrollment.course.title] = enrollment.course

    for idx, item_data in enumerate(items):
        item_kwargs = {
            "plan": plan,
            "item_type": item_data.get("type", "review"),
            "title": item_data.get("title", "Study task"),
            "description": item_data.get("description", ""),
            "priority": item_data.get("priority", "medium"),
            "estimated_minutes": item_data.get("minutes", 30),
            "order": idx + 1,
        }

        # Link to session if referenced
        session_id = item_data.get("session_id")
        if session_id and session_id in session_map:
            item_kwargs["session"] = session_map[session_id]
            item_kwargs["course"] = session_map[session_id].course

        # Link to quiz if referenced
        quiz_id = item_data.get("quiz_id")
        if quiz_id:
            try:
                item_kwargs["quiz"] = Quiz.objects.get(id=quiz_id)
            except Quiz.DoesNotExist:
                pass

        # Link to course by name
        course_name = item_data.get("course_name")
        if course_name and course_name in course_map:
            item_kwargs["course"] = course_map[course_name]

        # Parse due date
        due = item_data.get("due_date")
        if due:
            try:
                from datetime import datetime
                item_kwargs["due_date"] = datetime.strptime(due, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                pass

        StudyPlanItem.objects.create(**item_kwargs)

    return plan


def _generate_ai_study_plan(analytics, sessions, quizzes, weak_subjects, medium_subjects, student_name, logger):
    """Call OpenAI to generate study plan items. Returns empty on failure."""
    import json

    from django.conf import settings

    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return {"items": []}

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)

        prompt = f"""You are an expert educational planner creating a 2-week personalized study plan.

STUDENT: {student_name}
QUIZ AVERAGE: {analytics['quiz_performance']['avg_score']}% (trend: {analytics['quiz_performance']['trend']})
ATTENDANCE: {analytics['attendance_rate']}%
VELOCITY: {analytics['learning_velocity']} sessions/week
STUDY HOURS SO FAR: {analytics['total_study_hours']}

WEAK SUBJECTS (need most work): {json.dumps(weak_subjects)}
MEDIUM SUBJECTS (need reinforcement): {json.dumps(medium_subjects)}
AT-RISK COURSES: {json.dumps([{{'course': r['course'], 'progress': r['progress']}} for r in analytics['risk_courses']])}

UPCOMING SESSIONS (must attend):
{json.dumps(sessions, indent=2)}

AVAILABLE QUIZZES FOR PRACTICE:
{json.dumps(quizzes, indent=2)}

Create a study plan with 10-18 items. Respond with ONLY valid JSON (no markdown):
{{
  "plan_description": "Brief personalized description of this plan's goals",
  "daily_goal_minutes": <number based on student's current pace>,
  "weekly_goal_sessions": <realistic number>,
  "items": [
    {{
      "type": "session|quiz|review|practice|reading",
      "title": "Clear, specific title",
      "description": "Why this matters and how to approach it",
      "priority": "high|medium|low",
      "minutes": <estimated minutes>,
      "due_date": "YYYY-MM-DD or null",
      "session_id": <id from sessions list or null>,
      "quiz_id": <id from quizzes list or null>,
      "course_name": "course name or null"
    }}
  ]
}}

Rules:
- Include ALL upcoming sessions as "session" type items with their session_id
- Add review items for EACH weak subject with specific study strategies in the description
- Add quiz practice items using available quiz IDs for weak/medium subjects
- Add reading/practice items for at-risk courses
- Space items across the 2 weeks realistically
- Descriptions should be specific and helpful (e.g., "Focus on chapters 3-5 covering derivatives" not just "Review math")
- Set daily_goal_minutes based on their current velocity (don't overwhelm a slow learner)
- Prioritize: weak subjects and at-risk courses = high, medium subjects = medium, reinforcement = low
- If student has few weak areas, add stretch goals and advanced practice
- Make it feel achievable, not overwhelming"""

        model = getattr(settings, "AI_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1500,
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        if raw.startswith("json"):
            raw = raw[4:]

        return json.loads(raw.strip())

    except Exception as e:
        logger.warning(f"AI study plan generation failed: {e}")
        return {"items": []}


def _generate_fallback_plan_items(upcoming_sessions, weak_subjects, medium_subjects, available_quizzes, analytics):
    """Rule-based study plan item generation."""
    items = []

    # 1. Upcoming sessions
    for session in upcoming_sessions:
        items.append({
            "type": "session",
            "title": f"Attend: {session.title}",
            "description": f"Course: {session.course.title}. Prepare by reviewing previous session notes.",
            "priority": "high",
            "minutes": 90,
            "session_id": session.id,
            "due_date": session.start_time.strftime("%Y-%m-%d"),
        })

    # 2. Weak subject reviews
    for ss in weak_subjects[:5]:
        items.append({
            "type": "review",
            "title": f"Review: {ss.subject.name}",
            "description": f"Your score is {ss.strength_score:.0f}%. Go through the core concepts and rework problems you got wrong.",
            "priority": "high",
            "minutes": 45,
        })

    # 3. Quiz practice
    for q in available_quizzes[:4]:
        items.append({
            "type": "quiz",
            "title": f"Practice: {q['title']}",
            "description": f"Test your {q['subject']} knowledge. Aim for 70%+ to show improvement.",
            "priority": "medium",
            "minutes": 30,
            "quiz_id": q["id"],
        })

    # 4. At-risk course catch-up
    for rc in analytics.get("risk_courses", [])[:3]:
        items.append({
            "type": "reading",
            "title": f"Catch up: {rc['course']}",
            "description": f"Only {rc['progress']}% complete. Review missed materials and complete pending assignments.",
            "priority": "high",
            "minutes": 60,
            "course_name": rc["course"],
        })

    # 5. Medium subject reinforcement
    for ss in medium_subjects[:3]:
        items.append({
            "type": "practice",
            "title": f"Reinforce: {ss.subject.name}",
            "description": f"Score: {ss.strength_score:.0f}%. Practice with varied problems to solidify understanding.",
            "priority": "medium",
            "minutes": 30,
        })

    return items
