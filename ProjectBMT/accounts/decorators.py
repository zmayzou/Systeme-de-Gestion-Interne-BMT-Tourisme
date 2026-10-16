from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def has_metier_permission(user, permission_code):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    employe = getattr(user, 'employe', None)

    if not employe:
        return False

    if not employe.est_actif:
        return False

    if employe.permissions_metier.filter(code=permission_code).exists():
        return True

    if employe.role and employe.role.permissions.filter(
        code=permission_code
    ).exists():
        return True

    return False


def permission_required_metier(permission_code):
    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return redirect('login')

            if has_metier_permission(
                request.user,
                permission_code
            ):
                return view_func(request, *args, **kwargs)

            messages.error(
                request,
                "Vous n'avez pas la permission d'accéder à cette page."
            )

            return redirect('dashboard')

        return wrapper

    return decorator