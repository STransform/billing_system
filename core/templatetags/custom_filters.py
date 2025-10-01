from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replace all occurrences of `arg` in `value` with a space.
    """
    if not value:
        return value
    return value.replace(arg, ' ')