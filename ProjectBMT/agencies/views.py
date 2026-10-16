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

from notifications.models import HistoriqueAction

from .models import Agence


# =========================================================
# HELPERS - AGENCY SCOPING
# =========================================================


def get_accessible_agencies(user):

    agences = Agence.objects.all()

    # Admin / Directeur / Superuser
    if has_global_agency_access(user):
        return agences

    # Employé local
    agence = get_user_agence(user)

    if not agence:
        return agences.none()

    return agences.filter(
        id=agence.id
    )


def ensure_global_agency_management(request):
    """
    La gestion structurelle des agences
    est réservée aux utilisateurs globaux.
    """

    if has_global_agency_access(
        request.user
    ):
        return True

    messages.error(
        request,
        (
            "La gestion des agences est réservée "
            "à la direction ou à l'administration."
        )
    )

    return False


# =========================================================
# LISTE DES AGENCES
# =========================================================


@login_required
@permission_required_metier('agencies.view')
def agency_list(request):

    agences = (
        get_accessible_agencies(
            request.user
        )
        .order_by(
            'ville',
            'nom'
        )
    )

    return render(
        request,
        'agencies/agency_list.html',
        {
            'agences': agences,

            'employe': getattr(
                request.user,
                'employe',
                None
            ),

            'global_access': (
                has_global_agency_access(
                    request.user
                )
            ),
        }
    )


# =========================================================
# CREATION D'UNE AGENCE
# =========================================================


@login_required
@permission_required_metier('agencies.manage')
def agency_create(request):

    if not ensure_global_agency_management(
        request
    ):
        return redirect(
            'agency_list'
        )

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if request.method == 'POST':

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        ville = (
            request.POST.get(
                'ville'
            )
            or ''
        ).strip()

        adresse = (
            request.POST.get(
                'adresse'
            )
            or ''
        ).strip() or None

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip() or None

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip() or None

        # =================================================
        # VALIDATIONS
        # =================================================

        if not nom or not ville:

            messages.error(
                request,
                (
                    "Le nom et la ville "
                    "sont obligatoires."
                )
            )

            return render(
                request,
                'agencies/agency_form.html',
                {
                    'employe': employe,
                    'global_access': True,
                }
            )

        if Agence.objects.filter(
            nom__iexact=nom,
            ville__iexact=ville
        ).exists():

            messages.error(
                request,
                (
                    "Une agence avec ce nom "
                    "existe déjà dans cette ville."
                )
            )

            return render(
                request,
                'agencies/agency_form.html',
                {
                    'employe': employe,
                    'global_access': True,
                }
            )

        # =================================================
        # CREATION
        # =================================================

        agence = Agence.objects.create(
            nom=nom,
            ville=ville,
            adresse=adresse,
            telephone=telephone,
            email=email,
            est_active=True
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Création d'une agence",
            module="Agences",
            objet_id=agence.id,
            description=(
                f"Agence créée : "
                f"{agence.nom} - {agence.ville}"
            )
        )

        messages.success(
            request,
            "L'agence a été créée avec succès."
        )

        return redirect(
            'agency_list'
        )

    return render(
        request,
        'agencies/agency_form.html',
        {
            'employe': employe,
            'global_access': True,
        }
    )


# =========================================================
# MODIFICATION D'UNE AGENCE
# =========================================================


@login_required
@permission_required_metier('agencies.manage')
def agency_update(
    request,
    agency_id
):

    if not ensure_global_agency_management(
        request
    ):
        return redirect(
            'agency_list'
        )

    agence = get_object_or_404(
        Agence,
        id=agency_id
    )

    employe = getattr(
        request.user,
        'employe',
        None
    )

    if request.method == 'POST':

        ancien_nom = agence.nom
        ancienne_ville = agence.ville
        ancien_statut = agence.est_active

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        ville = (
            request.POST.get(
                'ville'
            )
            or ''
        ).strip()

        adresse = (
            request.POST.get(
                'adresse'
            )
            or ''
        ).strip() or None

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip() or None

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip() or None

        est_active = (
            request.POST.get(
                'est_active'
            )
            == 'on'
        )

        # =================================================
        # VALIDATIONS
        # =================================================

        if not nom or not ville:

            messages.error(
                request,
                (
                    "Le nom et la ville "
                    "sont obligatoires."
                )
            )

            return render(
                request,
                'agencies/agency_form.html',
                {
                    'agence': agence,
                    'employe': employe,
                    'global_access': True,
                }
            )

        if Agence.objects.filter(
            nom__iexact=nom,
            ville__iexact=ville
        ).exclude(
            id=agence.id
        ).exists():

            messages.error(
                request,
                (
                    "Une autre agence avec ce nom "
                    "existe déjà dans cette ville."
                )
            )

            return render(
                request,
                'agencies/agency_form.html',
                {
                    'agence': agence,
                    'employe': employe,
                    'global_access': True,
                }
            )

        # =================================================
        # UPDATE
        # =================================================

        agence.nom = nom
        agence.ville = ville
        agence.adresse = adresse
        agence.telephone = telephone
        agence.email = email
        agence.est_active = est_active

        agence.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Modification d'une agence",
            module="Agences",
            objet_id=agence.id,
            description=(
                f"Agence modifiée : "
                f"{agence.nom} - {agence.ville}"
            )
        )

        # =================================================
        # NOM / VILLE
        # =================================================

        if (
            ancien_nom != agence.nom
            or ancienne_ville != agence.ville
        ):

            HistoriqueAction.objects.create(
                employe=employe,
                action="Modification identité agence",
                module="Agences",
                objet_id=agence.id,
                description=(
                    f"{ancien_nom} - {ancienne_ville} → "
                    f"{agence.nom} - {agence.ville}"
                )
            )

        # =================================================
        # STATUT
        # =================================================

        if ancien_statut != agence.est_active:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Modification statut agence",
                module="Agences",
                objet_id=agence.id,
                description=(
                    "Statut : "
                    f"{'Active' if agence.est_active else 'Inactive'}"
                )
            )

        messages.success(
            request,
            "L'agence a été modifiée avec succès."
        )

        return redirect(
            'agency_list'
        )

    return render(
        request,
        'agencies/agency_form.html',
        {
            'agence': agence,
            'employe': employe,
            'global_access': True,
        }
    )


# =========================================================
# ACTIVER / DESACTIVER UNE AGENCE
# =========================================================


@login_required
@permission_required_metier('agencies.manage')
@require_POST
def agency_toggle_active(
    request,
    agency_id
):

    # Même si un employé local reçoit agencies.manage,
    # il ne peut pas modifier la structure des agences.

    if not ensure_global_agency_management(
        request
    ):
        return redirect(
            'agency_list'
        )

    agence = get_object_or_404(
        Agence,
        id=agency_id
    )

    employe = getattr(
        request.user,
        'employe',
        None
    )

    ancien_statut = (
        agence.est_active
    )

    agence.est_active = (
        not agence.est_active
    )

    agence.save(
        update_fields=[
            'est_active'
        ]
    )

    # =====================================================
    # HISTORIQUE
    # =====================================================

    HistoriqueAction.objects.create(
        employe=employe,
        action=(
            "Activation d'une agence"
            if agence.est_active
            else "Désactivation d'une agence"
        ),
        module="Agences",
        objet_id=agence.id,
        description=(
            f"Agence : {agence.nom} - {agence.ville} | "
            f"{'Active' if ancien_statut else 'Inactive'} → "
            f"{'Active' if agence.est_active else 'Inactive'}"
        )
    )

    if agence.est_active:

        messages.success(
            request,
            "L'agence a été activée."
        )

    else:

        messages.warning(
            request,
            "L'agence a été désactivée."
        )

    return redirect(
        'agency_list'
    )