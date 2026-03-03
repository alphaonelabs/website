"""
Views for documentation-style notes feature.

This module provides views for displaying and managing documentation notes,
including topic listings, section viewing, and progress tracking.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import (
    DocumentationNoteContent,
    DocumentationNoteProgress,
    DocumentationNoteSection,
    DocumentationNoteTopic,
)


@require_GET
def documentation_topics_list(request):
    """
    Display a list of all published documentation topics.

    Context:
        topics: QuerySet of published DocumentationNoteTopic objects
    """
    from django.db.models import Count

    topics = DocumentationNoteTopic.objects.filter(is_published=True).annotate(section_count=Count("sections"))

    user_progress = {}
    if request.user.is_authenticated:
        progress_records = DocumentationNoteProgress.objects.filter(user=request.user).values_list(
            "topic_id",
            "completion_percentage",
        )
        user_progress = {topic_id: completion for topic_id, completion in progress_records}

    context = {
        "topics": topics,
        "user_progress": user_progress,
    }
    return render(request, "documentation_notes/topics_list.html", context)


@require_GET
def documentation_topic_detail(request, topic_slug):
    """
    Display a documentation topic with its first section.

    Redirects to the first section of the topic if no section is specified.

    Args:
        topic_slug: The slug of the documentation topic

    Context:
        topic: The DocumentationNoteTopic object
        sections: QuerySet of sections for the topic
        current_section: The current section being viewed
        content: The content of the current section
        progress: User's progress on this topic (if authenticated)
        next_section: The next section (if available)
        previous_section: The previous section (if available)
    """
    topic = get_object_or_404(DocumentationNoteTopic, slug=topic_slug, is_published=True)
    sections = topic.sections.all()

    if not sections.exists():
        from django.http import Http404

        raise Http404("This topic has no sections yet.")

    # Get the first section or specified section
    first_section = sections.first()
    section = first_section

    # Load section content (allow sections with no content)
    content = DocumentationNoteContent.objects.filter(section=section).first()

    # Get user progress (read-only on GET - progress updates happen via POST only)
    progress = None
    if request.user.is_authenticated:
        progress, _ = DocumentationNoteProgress.objects.get_or_create(
            user=request.user,
            topic=topic,
        )

    section_ids = list(sections.values_list("id", flat=True))
    current_section_index = section_ids.index(section.id) + 1 if section.id in section_ids else 1

    context = {
        "topic": topic,
        "sections": sections,
        "current_section": section,
        "current_section_index": current_section_index,
        "content": content,
        "progress": progress,
        "next_section": section.get_next_section(),
        "previous_section": section.get_previous_section(),
    }
    return render(request, "documentation_notes/topic_detail.html", context)


@require_GET
def documentation_section_detail(request, topic_slug, section_slug):
    """
    Display a specific section of a documentation topic.

    Args:
        topic_slug: The slug of the documentation topic
        section_slug: The slug of the documentation section

    Context:
        topic: The DocumentationNoteTopic object
        sections: QuerySet of sections for the topic
        current_section: The current section being viewed
        content: The content of the current section
        progress: User's progress on this topic (if authenticated)
        next_section: The next section (if available)
        previous_section: The previous section (if available)
    """
    topic = get_object_or_404(DocumentationNoteTopic, slug=topic_slug, is_published=True)
    section = get_object_or_404(DocumentationNoteSection, slug=section_slug, topic=topic)
    sections = topic.sections.all()

    # Load section content (allow sections with no content)
    content = DocumentationNoteContent.objects.filter(section=section).first()

    # Get user progress (read-only on GET - progress updates happen via POST only)
    progress = None
    if request.user.is_authenticated:
        progress, _ = DocumentationNoteProgress.objects.get_or_create(
            user=request.user,
            topic=topic,
        )

    section_ids = list(sections.values_list("id", flat=True))
    current_section_index = section_ids.index(section.id) + 1 if section.id in section_ids else 1

    context = {
        "topic": topic,
        "sections": sections,
        "current_section": section,
        "current_section_index": current_section_index,
        "content": content,
        "progress": progress,
        "next_section": section.get_next_section(),
        "previous_section": section.get_previous_section(),
    }
    return render(request, "documentation_notes/topic_detail.html", context)


@login_required
@require_POST
def mark_section_viewed(request, topic_slug, section_slug):
    """
    AJAX endpoint to mark a section as viewed and update progress.

    Args:
        topic_slug: The slug of the documentation topic
        section_slug: The slug of the documentation section

    Returns:
        JSON response with updated progress data
    """
    topic = get_object_or_404(DocumentationNoteTopic, slug=topic_slug, is_published=True)
    section = get_object_or_404(DocumentationNoteSection, slug=section_slug, topic=topic)

    progress, _ = DocumentationNoteProgress.objects.get_or_create(
        user=request.user,
        topic=topic,
    )
    progress.mark_section_as_viewed(section)

    return JsonResponse(
        {
            "success": True,
            "completion_percentage": progress.completion_percentage,
            "sections_count": progress.sections_viewed.count(),
            "total_sections": topic.sections.count(),
        }
    )


@login_required
@require_GET
def user_progress(request):
    """
    Display user's progress on all documentation topics.

    Returns:
        JSON response with user progress data
    """
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        from django.http import Http404

        raise Http404()

    progress_records = DocumentationNoteProgress.objects.filter(user=request.user).values(
        "topic__title",
        "topic__slug",
        "completion_percentage",
        "completed_at",
    )

    return JsonResponse(
        {
            "progress": list(progress_records),
        }
    )
