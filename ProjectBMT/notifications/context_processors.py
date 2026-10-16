from .models import Notification


def notifications_count(request):

    if not request.user.is_authenticated:
        return {
            'unread_notifications_count': 0
        }

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if not employe:
        return {
            'unread_notifications_count': 0
        }

    count = Notification.objects.filter(
        employe=employe,
        est_lue=False
    ).count()

    return {
        'unread_notifications_count': count
    }