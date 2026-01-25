from django import template
from vendor_employees.utils import get_vendor_context
from vendor_employees.permissions import user_has_permission

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.simple_tag(takes_context=True)
def vendor_has_permission(context, code):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    vendor = get_vendor_context(request.user)
    if not vendor:
        return False
    return user_has_permission(request.user, vendor, code)
