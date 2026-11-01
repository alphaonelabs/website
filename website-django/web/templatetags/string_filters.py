from django import template

register = template.Library()


@register.filter
def trim(value):
    """Removes leading and trailing whitespace."""
    if value is None:
        return ""
    return str(value).strip()
