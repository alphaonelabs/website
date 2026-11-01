from django import template

register = template.Library()


@register.filter
def filter_rolled_over(sessions):
    """Check if there are any rolled over sessions that need confirmation."""
    return sessions.filter(is_rolled_over=True, teacher_confirmed=False).exists()
