# web/mass_class/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import Course, MassClassStream, Session


@login_required
def teacher_broadcast_view(request):
    """View for teachers to broadcast a Mass Class"""
    # Check if user is a teacher
    if not request.user.courses_teaching.exists():
        return redirect("dashboard")

    # Get recent courses taught by the user
    recent_courses = Course.objects.filter(teacher=request.user, status="published").order_by("-created_at")[:5]

    # Get upcoming sessions
    upcoming_sessions = Session.objects.filter(course__teacher=request.user, start_time__gte=timezone.now()).order_by(
        "start_time",
    )[:10]

    context = {
        "recent_courses": recent_courses,
        "upcoming_sessions": upcoming_sessions,
    }

    return render(request, "mass_class/teacher_broadcast.html", context)


@login_required
def manage_streams(request):
    """View for managing Mass Class streams"""
    # Get streams created by the user
    streams = MassClassStream.objects.filter(teacher=request.user).order_by("-created_at")

    context = {"streams": streams}

    return render(request, "mass_class/manage_streams.html", context)


@login_required
def student_view(request, session_id):
    """View for students to join a Mass Class"""
    # Get the stream
    stream = get_object_or_404(MassClassStream, stream_id=session_id)

    # Check if stream is active
    if stream.status not in ["initializing", "active"]:
        return render(request, "mass_class/stream_ended.html", {"stream": stream})

    context = {"stream": stream}

    return render(request, "mass_class/student_view.html", context)
