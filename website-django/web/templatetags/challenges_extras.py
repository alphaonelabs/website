from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Access a dictionary value by key in a template"""
    if dictionary and key and key in dictionary:
        return dictionary[key]
    return None
