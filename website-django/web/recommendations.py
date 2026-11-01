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
    return similar_courses[:limit]
