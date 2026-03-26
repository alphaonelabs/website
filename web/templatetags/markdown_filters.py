from typing import Any, Optional

import bleach
from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()

SAFE_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "br",
    "hr",
    "strong",
    "em",
    "b",
    "i",
    "u",
    "del",
    "ul",
    "ol",
    "li",
    "a",
    "pre",
    "code",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "img",
}

SAFE_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
    "td": {"align"},
    "th": {"align"},
}

ALLOWED_PROTOCOLS = {"http", "https", "mailto"}


def markdownify_sanitized(content: Optional[str]) -> str:
    """
    Custom markdownify function that sanitizes the output HTML using bleach.
    This is used both for template filters and for the markdownx AJAX preview.
    """
    if not content:
        return ""

    return bleach.clean(
        markdownify(content), tags=SAFE_TAGS, attributes=SAFE_ATTRIBUTES, protocols=ALLOWED_PROTOCOLS, strip=True
    )


@register.filter
def markdown(text: str) -> Any:
    """Convert markdown text to sanitized HTML."""
    return mark_safe(markdownify_sanitized(text))
