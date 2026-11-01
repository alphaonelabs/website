from django import template

from web.models import Cart

register = template.Library()


@register.filter
def get_cart_item_count(session_key):
    """Get the number of items in a guest user's cart."""
    try:
        cart = Cart.objects.get(session_key=session_key)
        return cart.item_count
    except Cart.DoesNotExist:
        return 0
