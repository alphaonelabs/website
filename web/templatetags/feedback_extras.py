import re

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def sub(value, arg):
    """Subtract the arg from the value."""
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) - float(arg)
        except (ValueError, TypeError):
            return ""


@register.filter
def growth_indicator(value):
    """Return a visual indicator based on growth value."""
    if not value or value == 0:
        return mark_safe('<span class="text-gray-500">⟶</span>')
    if value > 0:
        return mark_safe(f'<span class="text-green-600">▲ {value}</span>')
    else:
        return mark_safe(f'<span class="text-red-600">▼ {abs(value)}</span>')


@register.filter
def confidence_badge(value):
    """Return a color-coded badge based on confidence level."""
    if not value:
        return mark_safe('<span class="bg-gray-200 text-gray-700 py-1 px-2 rounded-full text-xs">N/A</span>')

    value = float(value)
    if value <= 1:
        return mark_safe('<span class="bg-red-100 text-red-600 py-1 px-2 rounded-full text-xs">Very Low</span>')
    elif value <= 2:
        return mark_safe('<span class="bg-red-50 text-orange-600 py-1 px-2 rounded-full text-xs">Low</span>')
    elif value <= 3:
        return mark_safe('<span class="bg-yellow-100 text-yellow-600 py-1 px-2 rounded-full text-xs">Medium</span>')
    elif value <= 4:
        return mark_safe('<span class="bg-green-100 text-green-600 py-1 px-2 rounded-full text-xs">Good</span>')
    else:
        return mark_safe('<span class="bg-green-200 text-green-700 py-1 px-2 rounded-full text-xs">Excellent</span>')


@register.filter
def extract_keywords(text, count=3):
    """Extract top keywords from text for quick display."""
    if not text:
        return ""

    # Simple keyword extraction - remove common words
    stop_words = set(
        [
            "the",
            "a",
            "an",
            "and",
            "is",
            "it",
            "to",
            "was",
            "for",
            "in",
            "on",
            "that",
            "be",
            "with",
            "as",
            "of",
            "this",
            "at",
            "from",
            "i",
            "my",
        ]
    )

    words = re.findall(r"\b\w+\b", text.lower())
    keywords = [word for word in words if word not in stop_words and len(word) > 3]

    # Count and sort by frequency
    from collections import Counter

    word_counts = Counter(keywords)

    # Get top keywords
    top_keywords = [word for word, _ in word_counts.most_common(int(count))]

    return ", ".join(top_keywords)
