"""Views for Chapter management."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import ChapterApplicationForm, ChapterEventForm, ChapterEventRSVPForm, ChapterForm
from .models import Chapter, ChapterApplication, ChapterEvent, ChapterEventRSVP, ChapterMembership


def chapter_directory(request):
    """Display directory of all active chapters."""
    chapters = Chapter.objects.filter(status="active").annotate(member_count=Count("memberships")).order_by("region")

    # Search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        chapters = chapters.filter(
            Q(name__icontains=search_query) | Q(region__icontains=search_query) | Q(country__icontains=search_query)
        )

    # Country filter
    country_filter = request.GET.get("country", "")
    if country_filter:
        chapters = chapters.filter(country=country_filter)

    # Get list of countries for filter dropdown
    countries = Chapter.objects.filter(status="active").values_list("country", flat=True).distinct().order_by("country")

    paginator = Paginator(chapters, 12)  # Show 12 chapters per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "countries": countries,
        "country_filter": country_filter,
    }
    return render(request, "web/chapters/directory.html", context)


def chapter_detail(request, slug):
    """Display chapter details."""
    chapter = get_object_or_404(Chapter, slug=slug)
    upcoming_events = chapter.events.filter(status="published", start_datetime__gte=timezone.now()).order_by(
        "start_datetime"
    )[:5]

    # Check if user is a member
    is_member = False
    user_membership = None
    if request.user.is_authenticated:
        try:
            user_membership = ChapterMembership.objects.get(chapter=chapter, user=request.user)
            is_member = user_membership.status == "active"
        except ChapterMembership.DoesNotExist:
            pass

    context = {
        "chapter": chapter,
        "upcoming_events": upcoming_events,
        "is_member": is_member,
        "user_membership": user_membership,
    }
    return render(request, "web/chapters/detail.html", context)


@login_required
def chapter_join(request, slug):
    """Join a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug, status="active")

    # Check if already a member
    membership, created = ChapterMembership.objects.get_or_create(
        chapter=chapter, user=request.user, defaults={"role": "participant", "status": "active"}
    )

    if created:
        messages.success(request, f"You have successfully joined {chapter.name}!")
    else:
        if membership.status == "inactive":
            membership.status = "active"
            membership.save()
            messages.success(request, f"Welcome back to {chapter.name}!")
        else:
            messages.info(request, f"You are already a member of {chapter.name}.")

    return redirect("chapter_detail", slug=slug)


@login_required
def chapter_leave(request, slug):
    """Leave a chapter."""
    chapter = get_object_or_404(Chapter, slug=slug)

    try:
        membership = ChapterMembership.objects.get(chapter=chapter, user=request.user)
        membership.status = "inactive"
        membership.save()
        messages.success(request, f"You have left {chapter.name}.")
    except ChapterMembership.DoesNotExist:
        messages.error(request, "You are not a member of this chapter.")

    return redirect("chapter_detail", slug=slug)


@login_required
def chapter_apply(request):
    """Apply to create a new chapter."""
    if request.method == "POST":
        form = ChapterApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.applicant = request.user
            application.save()
            messages.success(
                request,
                "Your chapter application has been submitted! We'll review it and get back to you soon.",
            )
            return redirect("chapter_directory")
    else:
        form = ChapterApplicationForm()

    context = {"form": form}
    return render(request, "web/chapters/apply.html", context)


@login_required
def chapter_applications(request):
    """View user's chapter applications."""
    applications = ChapterApplication.objects.filter(applicant=request.user).order_by("-created_at")

    context = {"applications": applications}
    return render(request, "web/chapters/applications.html", context)


@login_required
def chapter_event_list(request, chapter_slug):
    """List all events for a chapter."""
    chapter = get_object_or_404(Chapter, slug=chapter_slug)

    # Check if user is a member or leader
    is_member = False
    is_leader = False
    if request.user.is_authenticated:
        try:
            membership = ChapterMembership.objects.get(chapter=chapter, user=request.user, status="active")
            is_member = True
            is_leader = membership.role in ["leader", "co_organizer"]
        except ChapterMembership.DoesNotExist:
            pass

    # Filter events based on status
    if is_leader:
        events = chapter.events.all()
    else:
        events = chapter.events.filter(status="published")

    # Filter by upcoming/past
    event_filter = request.GET.get("filter", "upcoming")
    if event_filter == "upcoming":
        events = events.filter(start_datetime__gte=timezone.now())
    elif event_filter == "past":
        events = events.filter(start_datetime__lt=timezone.now())

    events = events.order_by("start_datetime")

    paginator = Paginator(events, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "chapter": chapter,
        "page_obj": page_obj,
        "is_member": is_member,
        "is_leader": is_leader,
        "event_filter": event_filter,
    }
    return render(request, "web/chapters/event_list.html", context)


def chapter_event_detail(request, chapter_slug, event_slug):
    """Display event details."""
    chapter = get_object_or_404(Chapter, slug=chapter_slug)
    event = get_object_or_404(ChapterEvent, chapter=chapter, slug=event_slug)

    # Check if user has RSVP'd
    user_rsvp = None
    if request.user.is_authenticated:
        try:
            user_rsvp = ChapterEventRSVP.objects.get(event=event, user=request.user)
        except ChapterEventRSVP.DoesNotExist:
            pass

    context = {
        "chapter": chapter,
        "event": event,
        "user_rsvp": user_rsvp,
    }
    return render(request, "web/chapters/event_detail.html", context)


@login_required
def chapter_event_create(request, chapter_slug):
    """Create a new event for a chapter."""
    chapter = get_object_or_404(Chapter, slug=chapter_slug)

    # Check if user is a leader or co-organizer
    try:
        membership = ChapterMembership.objects.get(chapter=chapter, user=request.user, status="active")
        if membership.role not in ["leader", "co_organizer"]:
            messages.error(request, "You must be a chapter leader or co-organizer to create events.")
            return redirect("chapter_detail", slug=chapter_slug)
    except ChapterMembership.DoesNotExist:
        messages.error(request, "You must be a member of this chapter to create events.")
        return redirect("chapter_detail", slug=chapter_slug)

    if request.method == "POST":
        form = ChapterEventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.chapter = chapter
            event.created_by = request.user
            event.save()
            messages.success(request, f"Event '{event.title}' has been created!")
            return redirect("chapter_event_detail", chapter_slug=chapter.slug, event_slug=event.slug)
    else:
        form = ChapterEventForm()

    context = {"form": form, "chapter": chapter}
    return render(request, "web/chapters/event_form.html", context)


@login_required
def chapter_event_rsvp(request, chapter_slug, event_slug):
    """RSVP to an event."""
    chapter = get_object_or_404(Chapter, slug=chapter_slug)
    event = get_object_or_404(ChapterEvent, chapter=chapter, slug=event_slug, status="published")

    # Check if event is full
    if event.is_full:
        messages.error(request, "This event is full.")
        return redirect("chapter_event_detail", chapter_slug=chapter_slug, event_slug=event_slug)

    rsvp, created = ChapterEventRSVP.objects.get_or_create(
        event=event, user=request.user, defaults={"status": "confirmed"}
    )

    if created:
        messages.success(request, f"You have RSVP'd to {event.title}!")
    else:
        if request.method == "POST":
            form = ChapterEventRSVPForm(request.POST, instance=rsvp)
            if form.is_valid():
                form.save()
                messages.success(request, "Your RSVP has been updated!")
        else:
            messages.info(request, "You have already RSVP'd to this event.")

    return redirect("chapter_event_detail", chapter_slug=chapter_slug, event_slug=event_slug)


@login_required
def chapter_event_cancel_rsvp(request, chapter_slug, event_slug):
    """Cancel RSVP to an event."""
    chapter = get_object_or_404(Chapter, slug=chapter_slug)
    event = get_object_or_404(ChapterEvent, chapter=chapter, slug=event_slug)

    try:
        rsvp = ChapterEventRSVP.objects.get(event=event, user=request.user)
        rsvp.delete()
        messages.success(request, "Your RSVP has been cancelled.")
    except ChapterEventRSVP.DoesNotExist:
        messages.error(request, "You have not RSVP'd to this event.")

    return redirect("chapter_event_detail", chapter_slug=chapter_slug, event_slug=event_slug)
