from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


def send_course_promotion_email(course, subject, template_name):
    """Send promotional emails about a course."""
    context = {"course": course, "course_url": course.get_absolute_url()}

    # Render email templates
    html_content = render_to_string(f"emails/{template_name}.html", context)
    text_content = strip_tags(html_content)

    # Send email
    send_mail(
        subject=subject,
        message=text_content,
        html_message=html_content,
        from_email=settings.EMAIL_FROM,
        recipient_list=[settings.EMAIL_FROM],  # Replace with actual recipient list
        fail_silently=False,
    )


def generate_social_share_content(course):
    """
    Generate social media sharing content for a course.

    Returns:
        dict: Content for different social platforms
    """
    # Basic course info
    title = course.title
    description = course.description[:200] + "..." if len(course.description) > 200 else course.description
    course_url = f"{settings.SITE_URL}/courses/{course.slug}/"

    # Generate hashtags from course subject and tags
    hashtags = [f"#{course.subject}"]
    if course.tags:
        hashtags.extend([f"#{tag.strip()}" for tag in course.tags.split(",")])
    hashtags = " ".join(hashtags)

    return {
        "twitter": {
            "text": f"Join my course: {title}\n\n{description[:100]}...\n\n{hashtags}\n{course_url}",
            "url": course_url,
        },
        "facebook": {
            "title": title,
            "description": description,
            "url": course_url,
            "hashtags": hashtags,
        },
        "linkedin": {
            "title": title,
            "description": description,
            "url": course_url,
        },
    }


def get_course_analytics(course):
    """
    Get analytics data for a course.

    Returns:
        dict: Analytics metrics
    """
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    seven_days_ago = now - timedelta(days=7)

    # Enrollment metrics
    total_enrollments = course.enrollments.count()
    recent_enrollments = course.enrollments.filter(enrollment_date__gte=thirty_days_ago).count()

    # Engagement metrics
    active_students = course.enrollments.filter(progress__last_accessed__gte=seven_days_ago).count()

    completion_rate = 0
    completed_students = course.enrollments.filter(status="completed").count()
    if total_enrollments > 0:
        completion_rate = (completed_students / total_enrollments) * 100

    # Revenue metrics
    total_revenue = sum(
        payment.amount for payment in course.enrollments.filter(payment__status="completed").select_related("payment")
    )
    recent_revenue = sum(
        payment.amount
        for payment in course.enrollments.filter(
            payment__status="completed", payment__created_at__gte=thirty_days_ago
        ).select_related("payment")
    )

    return {
        "enrollments": {
            "total": total_enrollments,
            "recent": recent_enrollments,
            "trend": ((recent_enrollments / total_enrollments * 100) if total_enrollments else 0),
        },
        "engagement": {
            "active_students": active_students,
            "completion_rate": completion_rate,
            "active_rate": ((active_students / total_enrollments * 100) if total_enrollments else 0),
        },
        "revenue": {
            "total": total_revenue,
            "recent": recent_revenue,
            "average_per_student": ((total_revenue / total_enrollments) if total_enrollments else 0),
        },
    }


def get_promotion_recommendations(course):
    """
    Get personalized recommendations for course promotion.

    Returns:
        list: Promotion recommendations
    """
    analytics = get_course_analytics(course)
    recommendations = []

    # Enrollment-based recommendations
    if analytics["enrollments"]["trend"] < 10:
        recommendations.append(
            {
                "type": "email_campaign",
                "priority": "high",
                "message": "Enrollment rate is low. Consider running an email campaign to reach potential students.",
                "action": "send_promotional_emails",
            }
        )

    # Engagement-based recommendations
    if analytics["engagement"]["active_rate"] < 50:
        recommendations.append(
            {
                "type": "content_update",
                "priority": "medium",
                "message": "Student engagement is low. Consider updating course content or adding new materials.",
                "action": "update_course_content",
            }
        )

    # Revenue-based recommendations
    if analytics["revenue"]["recent"] < analytics["revenue"]["total"] * 0.1:
        recommendations.append(
            {
                "type": "pricing_strategy",
                "priority": "medium",
                "message": "Recent revenue is lower than expected. Consider adjusting pricing or offering promotions.",
                "action": "review_pricing",
            }
        )

    # Social media recommendations
    if not course.tags:
        recommendations.append(
            {
                "type": "social_media",
                "priority": "low",
                "message": "Add relevant tags to improve course visibility in searches and social media.",
                "action": "add_course_tags",
            }
        )

    return recommendations
