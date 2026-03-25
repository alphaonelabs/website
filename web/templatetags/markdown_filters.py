import bleach
from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()

SAFE_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "br", "hr",
    "strong", "em", "b", "i", "u", "del",
    "ul", "ol", "li",
    "a",
    "pre", "code",
    "blockquote",
    "table", "thead", "tbody", "tr", "th", "td",
    "img",
}

SAFE_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
    "td": {"align"},
    "th": {"align"},
}

def markdownify_sanitized(content):
    """
    Custom markdownify function that sanitizes the output HTML using bleach.
    This is used both for template filters and for the markdownx AJAX preview.
    """
    if not content:
        return ""

    # Convert markdown to HTML
    html = markdownify(content)

    # Sanitize HTML
    clean_html = bleach.clean(
        html,
        tags=SAFE_TAGS,
        attributes=SAFE_ATTRIBUTES,
        strip=True
    )

    return clean_html


@register.filter
def markdown(text):
    """Convert markdown text to sanitized HTML."""
    clean_html = markdownify_sanitized(text)
    return mark_safe(clean_html)
