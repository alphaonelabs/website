from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()


@register.filter
def markdown(text):
    """Convert markdown text to HTML."""
    return mark_safe(markdownify(text))
