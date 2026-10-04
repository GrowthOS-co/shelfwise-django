from django import template

register = template.Library()


@register.filter
def money(cents):
    """1699 -> "$16.99"."""
    return f"${cents // 100:,}.{cents % 100:02d}"
