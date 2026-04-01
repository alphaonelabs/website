import bleach
from django import template
from django.utils.safestring import mark_safe
from markdownx.utils import markdownify

register = template.Library()

ALLOWED_TAGS = [
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
    "s",
    "del",
    "ul",
    "ol",
    "li",
    "a",
    "img",
    "pre",
    "code",
    "blockquote",
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    "div",
    "span",
    "sub",
    "sup",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "td": ["align"],
    "th": ["align"],
    "code": ["class"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto"]


@register.filter
def markdown(text: str) -> str:
    """Convert markdown text to sanitized HTML.
    
    Uses bleach to sanitize the HTML output from markdownify,
    preventing XSS attacks while preserving safe markdown formatting.
    
    Args:
        text (str): The markdown text to convert.
        
    Returns:
        str: Sanitized HTML string marked as safe.
    """
    if not isinstance(text, str):
        return ""

    html = markdownify(text)
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )
    return mark_safe(clean_html)
