import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Course, VirtualClassroom, VirtualClassroomWhiteboard
from .utils import can_access_classroom

# Add logger configuration
logger = logging.getLogger(__name__)


@login_required
def classroom_whiteboard(request, classroom_id):
    """
    Live whiteboard view for a specific virtual classroom/course.
    """
    # Get the classroom or course
    classroom = None
    course = None

    # First try to get by classroom_id
    try:
        classroom = get_object_or_404(VirtualClassroom, id=classroom_id)
        course = classroom.course
    except (VirtualClassroom.DoesNotExist, ValueError):
        # If not found, try to get by course ID
        try:
            course = get_object_or_404(Course, id=classroom_id)
            # Try to get existing classroom for this course
            try:
                classroom = VirtualClassroom.objects.get(course=course)
            except VirtualClassroom.DoesNotExist:
                # Create a virtual classroom for this course if it doesn't exist
                classroom = VirtualClassroom.objects.create(
                    name=f"{course.title} - Virtual Classroom", teacher=course.teacher, course=course
                )
        except (Course.DoesNotExist, ValueError):
            messages.error(request, "Classroom or course not found.")
            return redirect("virtual_classroom_list")

    # Check if user has access (teacher or enrolled student)
    is_teacher = classroom.teacher == request.user
    is_enrolled = can_access_classroom(request.user, classroom)

    if not is_enrolled:
        messages.error(request, "You don't have access to this classroom.")
        return redirect("virtual_classroom_list")

    # Get or create whiteboard for this classroom
    whiteboard, created = VirtualClassroomWhiteboard.objects.get_or_create(
        classroom=classroom, defaults={"canvas_data": {}, "last_updated_by": request.user}
    )

    context = {
        "classroom": classroom,
        "course": course,
        "whiteboard": whiteboard,
        "is_teacher": is_teacher,
        "is_enrolled": is_enrolled,
        "classroom_id": classroom.id,
        "room_name": f"whiteboard_{classroom.id}",
    }

    return render(request, "virtual_classroom/live_whiteboard.html", context)


@login_required
@require_POST
def save_whiteboard_data(request, classroom_id):
    """
    Save whiteboard canvas data via AJAX.
    """
    try:
        classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

        # Check permissions
        if not can_access_classroom(request.user, classroom):
            return JsonResponse({"error": "Access denied"}, status=403)

        # Get whiteboard
        whiteboard, created = VirtualClassroomWhiteboard.objects.get_or_create(
            classroom=classroom, defaults={"canvas_data": {}, "last_updated_by": request.user}
        )

        # Parse the request data
        data = json.loads(request.body)
        canvas_data = data.get("canvas_data", {})
        background_image = data.get("background_image", "")

        # Update whiteboard
        whiteboard.canvas_data = canvas_data
        if background_image:
            whiteboard.background_image = background_image
        whiteboard.last_updated_by = request.user
        whiteboard.save()

        return JsonResponse({"success": True, "message": "Whiteboard saved successfully"})

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "error": "Invalid request data",
            },
            status=400,
        )
    except Exception:
        return JsonResponse(
            {
                "error": "An error occurred while saving the whiteboard",
            },
            status=500,
        )


@login_required
def get_whiteboard_data(request, classroom_id):
    """
    Get current whiteboard data for loading.
    """
    try:
        classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

        # Check permissions
        if not can_access_classroom(request.user, classroom):
            return JsonResponse({"error": "Access denied"}, status=403)

        # Get whiteboard
        try:
            whiteboard = VirtualClassroomWhiteboard.objects.get(classroom=classroom)

            # Extract canvas data from the wrapper format
            canvas_data = whiteboard.canvas_data
            if isinstance(canvas_data, dict) and "data" in canvas_data:
                canvas_data = canvas_data["data"]  # Extract the actual base64 string

            return JsonResponse(
                {
                    "canvas_data": canvas_data,
                    "background_image": whiteboard.background_image or "",
                    "last_updated": whiteboard.last_updated.isoformat(),
                    "last_updated_by": whiteboard.last_updated_by.username if whiteboard.last_updated_by else None,
                }
            )
        except VirtualClassroomWhiteboard.DoesNotExist:
            return JsonResponse(
                {"canvas_data": {}, "background_image": "", "last_updated": None, "last_updated_by": None}
            )

    except Exception:
        return JsonResponse(
            {
                "error": "An error occurred while retrieving whiteboard data",
            },
            status=500,
        )


@login_required
@require_POST
def clear_whiteboard(request, classroom_id):
    """
    Clear the whiteboard canvas.
    """
    try:
        classroom = get_object_or_404(VirtualClassroom, id=classroom_id)

        # Check if user is teacher (only teachers can clear)
        if classroom.teacher != request.user:
            return JsonResponse({"error": "Only teachers can clear the whiteboard"}, status=403)

        # Get whiteboard
        try:
            whiteboard = VirtualClassroomWhiteboard.objects.get(classroom=classroom)
            whiteboard.canvas_data = {}
            whiteboard.background_image = ""
            whiteboard.last_updated_by = request.user
            whiteboard.save()

            return JsonResponse({"success": True, "message": "Whiteboard cleared successfully"})
        except VirtualClassroomWhiteboard.DoesNotExist:
            return JsonResponse({"success": True, "message": "Whiteboard was already empty"})

    except Exception as e:
        # Log the detailed exception for debugging
        logger.exception("Error in clear_whiteboard: %s", str(e))
        return JsonResponse({"error": "An internal error occurred"}, status=500)
