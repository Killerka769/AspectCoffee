"""Custom template tags for the users app."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def get_dismissed_notices(context):
    """Return the list of notice keys the user has dismissed in this session."""
    request = context.get("request")
    if request is None:
        return []
    return list(request.session.get("dismissed_notices", []))
