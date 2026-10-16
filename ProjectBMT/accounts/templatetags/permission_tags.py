from django import template
from accounts.decorators import has_metier_permission

register = template.Library()


@register.filter
def has_perm_metier(user, permission_code):
    return has_metier_permission(user, permission_code)