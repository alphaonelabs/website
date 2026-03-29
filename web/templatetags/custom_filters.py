from collections.abc import Mapping
from typing import Any

from django import template

register = template.Library()


@register.filter
def get_item(dictionary: Mapping[str, Any] | Any, key: str) -> Any:
    """
    Custom template filter to access dictionary values by key.
    Usage: {{ store_product_counts|get_item:name }}
    Returns 0 if key doesn't exist.
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, 0)
    return 0
