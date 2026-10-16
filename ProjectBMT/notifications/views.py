from django.contrib.auth.decorators import login_required
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from django.contrib import messages
from django.views.decorators.http import require_POST

from accounts.decorators import (
    permission_required_metier
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from .models import (
    Notification,
    HistoriqueAction
)


# =========================================================
# NOTIFICATIONS
# =========================================================


@login_required
def notification_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if not employe:

        messages.error(
            request,
            "Aucun profil employé associé à ce compte."
        )

        return redirect(
            'dashboard'
        )

    notifications = (
        Notification.objects
        .filter(
            employe=employe
        )
        .order_by(
            '-date_creation'
        )
    )

    return render(
        request,
        'notifications/notification_list.html',
        {
            'notifications': notifications,
            'employe': employe,
        }
    )


# =========================================================
# MARQUER UNE NOTIFICATION COMME LUE
# =========================================================


@login_required
@require_POST
def notification_mark_read(
    request,
    notification_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if not employe:

        messages.error(
            request,
            "Aucun profil employé associé à ce compte."
        )

        return redirect(
            'dashboard'
        )

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        employe=employe
    )

    if not notification.est_lue:

        notification.est_lue = True

        notification.save(
            update_fields=[
                'est_lue'
            ]
        )

    return redirect(
        'notification_list'
    )


# =========================================================
# MARQUER TOUTES COMME LUES
# =========================================================


@login_required
@require_POST
def notification_mark_all_read(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if not employe:

        messages.error(
            request,
            "Aucun profil employé associé à ce compte."
        )

        return redirect(
            'dashboard'
        )

    Notification.objects.filter(
        employe=employe,
        est_lue=False
    ).update(
        est_lue=True
    )

    messages.success(
        request,
        (
            "Toutes les notifications ont été "
            "marquées comme lues."
        )
    )

    return redirect(
        'notification_list'
    )


# =========================================================
# SUPPRIMER UNE NOTIFICATION
# =========================================================


@login_required
@require_POST
def notification_delete(
    request,
    notification_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if not employe:

        messages.error(
            request,
            "Aucun profil employé associé à ce compte."
        )

        return redirect(
            'dashboard'
        )

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        employe=employe
    )

    notification.delete()

    messages.success(
        request,
        "La notification a été supprimée."
    )

    return redirect(
        'notification_list'
    )


# =========================================================
# HISTORIQUE DES ACTIONS
# =========================================================


@login_required
@permission_required_metier('reports.view')
def historique_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    global_access = (
        has_global_agency_access(
            request.user
        )
    )

    agence = get_user_agence(
        request.user
    )

    historique = (
        HistoriqueAction.objects
        .select_related(
            'employe',
            'employe__user',
            'employe__role',
            'employe__agence'
        )
    )

    # =====================================================
    # AGENCY SCOPING
    # =====================================================

    if global_access:

        pass

    elif agence:

        historique = historique.filter(
            employe__agence=agence
        )

    else:

        historique = historique.none()

    historique = historique.order_by(
        '-date_action'
    )

    return render(
        request,
        'notifications/historique_list.html',
        {
            'historique': historique,
            'employe': employe,
            'global_access': global_access,
            'agence': agence,
        }
    )