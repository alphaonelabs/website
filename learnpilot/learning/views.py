"""Views for the learning app."""

from __future__ import annotations

import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from .ai.adaptive import get_adaptive_curriculum
from .ai.cloudflare_ai import CloudflareAIError
from .ai.tutor import get_tutor
from .models import (
    AdaptivePath,
    Course,
    Lesson,
    LearnerProfile,
    LearningSession,
    Message,
    PathLesson,
    Progress,
    Topic,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_profile(user) -> LearnerProfile:
    profile, _ = LearnerProfile.objects.get_or_create(user=user)
    return profile


def _progress_map(profile: LearnerProfile) -> dict[int, Progress]:
    """Return a mapping of lesson_id → Progress for the given profile."""
    return {p.lesson_id: p for p in profile.progress_records.all()}


# ---------------------------------------------------------------------------
# Home / landing page
# ---------------------------------------------------------------------------

class HomeView(TemplateView):
    template_name = "learning/home.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("dashboard")
        return super().get(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "learning/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = _get_or_create_profile(self.request.user)
        profile.update_activity()

        progress_qs = profile.progress_records.select_related("lesson__course__topic").filter(completed=True)
        completed_lessons = progress_qs.count()
        recent_progress = progress_qs.order_by("-completed_at")[:5]

        active_sessions = profile.sessions.filter(is_active=True).select_related("lesson__course")
        paths = profile.adaptive_paths.filter(is_active=True).select_related("topic")[:3]

        ctx.update(
            {
                "profile": profile,
                "completed_lessons": completed_lessons,
                "recent_progress": recent_progress,
                "active_sessions": active_sessions,
                "adaptive_paths": paths,
                "topics": Topic.objects.all()[:6],
            }
        )
        return ctx


# ---------------------------------------------------------------------------
# Courses
# ---------------------------------------------------------------------------

class CourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "learning/course_list.html"
    context_object_name = "courses"

    def get_queryset(self):
        qs = Course.objects.filter(is_published=True).select_related("topic")
        topic_id = self.request.GET.get("topic")
        difficulty = self.request.GET.get("difficulty")
        if topic_id:
            qs = qs.filter(topic_id=topic_id)
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["topics"] = Topic.objects.all()
        ctx["selected_topic"] = self.request.GET.get("topic")
        ctx["selected_difficulty"] = self.request.GET.get("difficulty")
        return ctx


class CourseDetailView(LoginRequiredMixin, DetailView):
    model = Course
    template_name = "learning/course_detail.html"
    context_object_name = "course"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = _get_or_create_profile(self.request.user)
        prog_map = _progress_map(profile)
        lessons = self.object.lessons.all()
        lesson_data = [
            {
                "lesson": l,
                "progress": prog_map.get(l.pk),
            }
            for l in lessons
        ]
        ctx["lesson_data"] = lesson_data
        ctx["profile"] = profile
        return ctx


# ---------------------------------------------------------------------------
# Adaptive path generation
# ---------------------------------------------------------------------------

@login_required
def generate_path_view(request, topic_id: int):
    topic = get_object_or_404(Topic, pk=topic_id)
    profile = _get_or_create_profile(request.user)

    if request.method == "POST":
        try:
            available = list(
                topic.courses.filter(is_published=True)
                .values_list("lessons__id", "lessons__title", "lessons__lesson_type", "lessons__course__difficulty")
                .order_by("lessons__course__difficulty", "lessons__order")
            )
            lesson_dicts = [
                {"id": row[0], "title": row[1], "type": row[2], "difficulty": row[3]}
                for row in available
                if row[0] is not None
            ]

            curriculum = get_adaptive_curriculum()
            result = curriculum.generate_learning_path(
                topic_name=topic.name,
                skill_level=profile.skill_level,
                learning_style=profile.learning_style,
                available_lessons=lesson_dicts,
                goals=request.POST.get("goals", ""),
            )

            # Deactivate old paths for this topic
            profile.adaptive_paths.filter(topic=topic, is_active=True).update(is_active=False)

            path = AdaptivePath.objects.create(
                learner=profile,
                topic=topic,
                rationale=result.get("rationale", ""),
            )
            ordered_ids = result.get("ordered_lesson_ids", [])
            for order, lesson_id in enumerate(ordered_ids):
                try:
                    lesson = Lesson.objects.get(pk=lesson_id)
                    PathLesson.objects.create(path=path, lesson=lesson, order=order)
                except Lesson.DoesNotExist:
                    pass

            messages.success(request, f'Your personalised path for "{topic.name}" is ready!')
            return redirect("adaptive_path_detail", pk=path.pk)

        except CloudflareAIError as exc:
            logger.error("CloudflareAIError generating path: %s", exc)
            messages.error(request, "Could not reach AI service. Please try again later.")

    return render(request, "learning/generate_path.html", {"topic": topic, "profile": profile})


class AdaptivePathDetailView(LoginRequiredMixin, DetailView):
    model = AdaptivePath
    template_name = "learning/adaptive_path.html"
    context_object_name = "path"

    def get_queryset(self):
        profile = _get_or_create_profile(self.request.user)
        return AdaptivePath.objects.filter(learner=profile)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = _get_or_create_profile(self.request.user)
        prog_map = _progress_map(profile)
        path_lessons = (
            self.object.pathlesson_set.select_related("lesson__course").order_by("order")
        )
        ctx["path_lessons"] = [
            {"pl": pl, "progress": prog_map.get(pl.lesson_id)}
            for pl in path_lessons
        ]
        return ctx


# ---------------------------------------------------------------------------
# Tutoring session
# ---------------------------------------------------------------------------

@login_required
def start_session_view(request, lesson_id: int):
    lesson = get_object_or_404(Lesson, pk=lesson_id)
    profile = _get_or_create_profile(request.user)

    # Reuse an existing active session or create a new one
    session = profile.sessions.filter(lesson=lesson, is_active=True).first()
    if not session:
        session = LearningSession.objects.create(learner=profile, lesson=lesson)
        # Seed with an opening message from the tutor
        try:
            tutor = get_tutor()
            greeting = tutor.explain_concept(
                concept=lesson.title,
                skill_level=profile.skill_level,
                learning_style=profile.learning_style,
                context=lesson.content[:500],
            )
        except CloudflareAIError:
            greeting = (
                f'Welcome to "{lesson.title}"! I\'m your AI tutor. '
                "Ask me anything about this lesson."
            )
        Message.objects.create(session=session, role="assistant", content=greeting)

    return redirect("tutor_session", session_id=session.pk)


class TutorSessionView(LoginRequiredMixin, View):
    template_name = "learning/session.html"

    def get(self, request, session_id: int):
        profile = _get_or_create_profile(request.user)
        session = get_object_or_404(LearningSession, pk=session_id, learner=profile)
        chat_history = session.messages.order_by("created_at")
        prog, _ = Progress.objects.get_or_create(learner=profile, lesson=session.lesson)

        return render(
            request,
            self.template_name,
            {
                "session": session,
                "chat_history": chat_history,
                "progress": prog,
                "profile": profile,
            },
        )


@login_required
def tutor_chat_api(request, session_id: int):
    """AJAX endpoint: receive a learner message, return AI tutor response."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    profile = _get_or_create_profile(request.user)
    session = get_object_or_404(LearningSession, pk=session_id, learner=profile)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_message = body.get("message", "").strip()
    if not user_message:
        return JsonResponse({"error": "Empty message"}, status=400)

    # Persist learner message
    Message.objects.create(session=session, role="user", content=user_message)

    # Build conversation history (last 20 messages, excluding the one just added)
    all_messages = list(
        session.messages.exclude(role="system").order_by("created_at").values("role", "content")
    )
    # Exclude the last message (the user message just persisted) so it's passed separately
    history = all_messages[:-1][-20:]

    try:
        tutor = get_tutor()
        ai_response = tutor.continue_conversation(
            history=history,
            user_message=user_message,
            lesson_context=session.lesson.content[:800],
        )
    except CloudflareAIError as exc:
        logger.error("CloudflareAIError in chat: %s", exc)
        ai_response = "I'm having trouble connecting to my AI backend right now. Please try again in a moment."

    # Persist tutor message
    msg = Message.objects.create(session=session, role="assistant", content=ai_response)
    return JsonResponse(
        {
            "response": ai_response,
            "message_id": msg.pk,
            "timestamp": msg.created_at.isoformat(),
        }
    )


@login_required
def end_session_view(request, session_id: int):
    """End a tutoring session, generate a summary, and update progress."""
    profile = _get_or_create_profile(request.user)
    session = get_object_or_404(LearningSession, pk=session_id, learner=profile)

    if session.is_active:
        session.end_session()

    # Generate summary
    conversation = [
        {"role": m.role, "content": m.content}
        for m in session.messages.order_by("created_at")
    ]
    try:
        tutor = get_tutor()
        summary = tutor.generate_session_summary(
            conversation=conversation,
            lesson_title=session.lesson.title,
        )
    except CloudflareAIError:
        summary = "Session completed."

    # Update progress
    prog, _ = Progress.objects.get_or_create(learner=profile, lesson=session.lesson)
    prog.attempts += 1
    prog.time_spent_seconds += session.duration_seconds()
    if not prog.completed:
        # Mark as completed with a default score of 0.7 for finishing the session
        prog.mark_complete(score=0.7)
    else:
        prog.save()

    return render(
        request,
        "learning/session_end.html",
        {"session": session, "summary": summary, "progress": prog},
    )


# ---------------------------------------------------------------------------
# Practice & feedback
# ---------------------------------------------------------------------------

@login_required
def practice_question_api(request, lesson_id: int):
    """Return an AI-generated practice question for the lesson."""
    if request.method != "GET":
        return JsonResponse({"error": "GET required"}, status=405)

    lesson = get_object_or_404(Lesson, pk=lesson_id)
    profile = _get_or_create_profile(request.user)

    try:
        tutor = get_tutor()
        question = tutor.generate_practice_question(
            topic=lesson.title,
            difficulty=lesson.course.difficulty,
            question_type="open-ended",
        )
    except CloudflareAIError as exc:
        logger.error("CloudflareAIError generating question: %s", exc)
        return JsonResponse({"error": "AI service unavailable"}, status=503)

    return JsonResponse({"question": question, "lesson_id": lesson_id})


@login_required
def evaluate_answer_api(request):
    """Evaluate a learner's answer and return score + feedback."""
    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()
    lesson_id = body.get("lesson_id")

    if not question or not answer:
        return JsonResponse({"error": "question and answer required"}, status=400)

    topic = ""
    if lesson_id:
        lesson = Lesson.objects.filter(pk=lesson_id).first()
        if lesson:
            topic = lesson.title

    try:
        tutor = get_tutor()
        result = tutor.evaluate_answer(question=question, learner_answer=answer, topic=topic)
    except CloudflareAIError as exc:
        logger.error("CloudflareAIError evaluating answer: %s", exc)
        return JsonResponse({"error": "AI service unavailable"}, status=503)

    # Optionally update progress score
    if lesson_id:
        profile = _get_or_create_profile(request.user)
        prog, _ = Progress.objects.get_or_create(learner=profile, lesson_id=lesson_id)
        score = float(result.get("score", 0.5))
        if score > prog.score:
            prog.score = score
            prog.attempts += 1
            if score >= 0.8 and not prog.completed:
                prog.mark_complete(score=score)
            else:
                prog.save()

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Progress
# ---------------------------------------------------------------------------

class ProgressView(LoginRequiredMixin, TemplateView):
    template_name = "learning/progress.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = _get_or_create_profile(self.request.user)
        progress_qs = (
            profile.progress_records
            .select_related("lesson__course__topic")
            .order_by("lesson__course__topic__name", "lesson__order")
        )

        # Group by topic
        by_topic: dict[str, list] = {}
        for p in progress_qs:
            topic_name = p.lesson.course.topic.name
            by_topic.setdefault(topic_name, []).append(p)

        # Adaptive recommendations
        recommendations = []
        recent_scores = [p.score for p in progress_qs if p.completed][-5:]
        for topic in Topic.objects.all():
            incomplete = (
                Lesson.objects.filter(course__topic=topic, course__is_published=True)
                .exclude(progress_records__learner=profile, progress_records__completed=True)
                .select_related("course")[:3]
            )
            if incomplete.exists():
                recommendations.append({"topic": topic, "lessons": incomplete})
            if len(recommendations) >= 3:
                break

        try:
            if by_topic and recent_scores:
                curriculum = get_adaptive_curriculum()
                topic_name = next(iter(by_topic))
                insights = curriculum.generate_progress_insights(
                    learner_name=self.request.user.username,
                    topic_name=topic_name,
                    progress_data=[
                        {
                            "lesson": p.lesson.title,
                            "score": p.score,
                            "completed": p.completed,
                            "attempts": p.attempts,
                        }
                        for p in progress_qs[:10]
                    ],
                )
            else:
                insights = ""
        except CloudflareAIError:
            insights = ""

        ctx.update(
            {
                "profile": profile,
                "progress_by_topic": by_topic,
                "recommendations": recommendations,
                "insights": insights,
            }
        )
        return ctx
