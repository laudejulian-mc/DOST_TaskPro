import json
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='to_json')
def to_json(value):
    """Convert Python dict to JSON for JavaScript - returns safe markup"""
    if value is None:
        return mark_safe('null')
    try:
        # If it's already a string (serialized JSON), parse and re-dump
        if isinstance(value, str):
            value = json.loads(value)
        return mark_safe(json.dumps(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return mark_safe('null')
