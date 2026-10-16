from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from accounts.decorators import permission_required_metier
from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from notifications.models import HistoriqueAction

from .models import Billet
from dossiers.models import Dossier
from accounts.models import Employe


# =========================================================
# CONSTANTES
# =========================================================

TYPES_BILLET_AUTORISES = [
    'AVION',
    'TRAIN',
    'BUS',
    'AUTRE',
]

STATUTS_BILLET_AUTORISES = [
    'EN_ATTENTE',
    'RESERVE',
    'BILLET_EMIS',
    'ANNULE',
    'MODIFIE',
]


# =========================================================
# HELPERS - AGENCY SCOPING
# =========================================================


def get_accessible_dossiers(user):

    dossiers = Dossier.objects.all()

    if has_global_agency_access(user):
        return dossiers

    agence = get_user_agence(user)

    if not agence:
        return dossiers.none()

    return dossiers.filter(
        agence=agence
    )


def get_accessible_billets(user):

    billets = Billet.objects.all()

    if has_global_agency_access(user):
        return billets

    agence = get_user_agence(user)

    if not agence:
        return billets.none()

    return billets.filter(
        dossier__agence=agence
    )


def get_accessible_responsables(user):

    responsables = Employe.objects.filter(
        est_actif=True,
        role__nom='Agent Billetterie'
    ).select_related(
        'user',
        'role',
        'agence'
    )

    if has_global_agency_access(user):
        return responsables

    agence = get_user_agence(user)

    if not agence:
        return responsables.none()

    return responsables.filter(
        agence=agence
    )


# =========================================================
# HELPER - DATETIME
# =========================================================


def convertir_datetime(valeur):
    """
    Convertit une valeur provenant d'un input datetime-local
    en objet datetime Django.

    Retourne None si la valeur est vide ou invalide.
    """

    if not valeur:
        return None

    valeur = valeur.strip()

    date_obj = parse_datetime(
        valeur
    )

    if date_obj is None:
        return None

    # Si USE_TZ=True, on rend la date timezone-aware.
    if (
        timezone.is_naive(date_obj)
        and timezone.is_aware(timezone.now())
    ):
        date_obj = timezone.make_aware(
            date_obj,
            timezone.get_current_timezone()
        )

    return date_obj


# =========================================================
# HELPER - FORM
# =========================================================


def render_billet_form(
    request,
    dossiers,
    responsables,
    employe,
    billet=None
):

    context = {
        'dossiers': dossiers,
        'responsables': responsables,
        'employe': employe,
    }

    if billet is not None:
        context['billet'] = billet

    return render(
        request,
        'ticketing/billet_form.html',
        context
    )


# =========================================================
# LISTE DES BILLETS
# =========================================================


@login_required
@permission_required_metier('ticketing.view')
def billet_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    billets = get_accessible_billets(
        request.user
    ).select_related(
        'dossier',
        'dossier__client',
        'dossier__agence',
        'responsable',
        'responsable__user',
        'responsable__agence'
    ).order_by(
        '-date_creation'
    )

    return render(
        request,
        'ticketing/billet_list.html',
        {
            'billets': billets,
            'employe': employe,
            'global_access': has_global_agency_access(
                request.user
            ),
        }
    )


# =========================================================
# CREATION BILLET
# =========================================================


@login_required
@permission_required_metier('ticketing.manage')
def billet_create(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).filter(
        type_service='BILLETTERIE'
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    responsables = get_accessible_responsables(
        request.user
    )

    if request.method == 'POST':

        dossier_id = request.POST.get(
            'dossier'
        )

        responsable_id = (
            request.POST.get(
                'responsable'
            )
            or None
        )

        type_billet = request.POST.get(
            'type_billet'
        )

        compagnie = (
            request.POST.get(
                'compagnie'
            )
            or ''
        ).strip()

        ville_depart = (
            request.POST.get(
                'ville_depart'
            )
            or ''
        ).strip()

        ville_arrivee = (
            request.POST.get(
                'ville_arrivee'
            )
            or ''
        ).strip()

        date_depart_raw = (
            request.POST.get(
                'date_depart'
            )
            or ''
        ).strip()

        date_retour_raw = (
            request.POST.get(
                'date_retour'
            )
            or ''
        ).strip()

        prix_raw = (
            request.POST.get(
                'prix'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or 'EN_ATTENTE'
        )

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # RESPONSABLE
        # =================================================

        responsable = None

        if responsable_id:

            responsable = get_object_or_404(
                responsables,
                id=responsable_id
            )

        # =================================================
        # TYPE
        # =================================================

        if type_billet not in TYPES_BILLET_AUTORISES:

            messages.error(
                request,
                "Le type de billet est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in STATUTS_BILLET_AUTORISES:

            messages.error(
                request,
                "Le statut du billet est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        # =================================================
        # COMPAGNIE / VILLES
        # =================================================

        if not compagnie:

            messages.error(
                request,
                "La compagnie est obligatoire."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        if not ville_depart or not ville_arrivee:

            messages.error(
                request,
                (
                    "La ville de départ et la ville "
                    "d'arrivée sont obligatoires."
                )
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        # =================================================
        # DATE DE DEPART
        # =================================================

        if not date_depart_raw:

            messages.error(
                request,
                "La date de départ est obligatoire."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        date_depart = convertir_datetime(
            date_depart_raw
        )

        if date_depart is None:

            messages.error(
                request,
                "La date de départ est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe
            )

        # =================================================
        # DATE DE RETOUR
        # =================================================

        date_retour = None

        if date_retour_raw:

            date_retour = convertir_datetime(
                date_retour_raw
            )

            if date_retour is None:

                messages.error(
                    request,
                    "La date de retour est invalide."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe
                )

            if date_retour < date_depart:

                messages.error(
                    request,
                    (
                        "La date de retour ne peut pas "
                        "être antérieure à la date de départ."
                    )
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe
                )

        # =================================================
        # PRIX
        # =================================================

        prix = None

        if prix_raw:

            try:

                prix = Decimal(
                    prix_raw
                )

            except InvalidOperation:

                messages.error(
                    request,
                    "Le prix du billet est invalide."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe
                )

            if prix < 0:

                messages.error(
                    request,
                    "Le prix ne peut pas être négatif."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe
                )

        # =================================================
        # CREATION
        # =================================================

        billet = Billet.objects.create(
            dossier=dossier,
            responsable=responsable,
            type_billet=type_billet,
            compagnie=compagnie,

            reference_reservation=(
                request.POST.get(
                    'reference_reservation'
                )
                or ''
            ).strip() or None,

            ville_depart=ville_depart,
            ville_arrivee=ville_arrivee,

            date_depart=date_depart,
            date_retour=date_retour,

            prix=prix,
            statut=statut,

            commentaire=(
                request.POST.get(
                    'commentaire'
                )
                or ''
            ).strip() or None,
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Création d'un billet",
            module="Billetterie",
            objet_id=billet.id,
            description=(
                f"Billet créé pour le dossier "
                f"{billet.dossier.numero_dossier} : "
                f"{billet.ville_depart} → "
                f"{billet.ville_arrivee} - "
                f"Agence : {billet.dossier.agence}"
            )
        )

        messages.success(
            request,
            "Le billet a été créé avec succès."
        )

        return redirect(
            'billet_detail',
            billet_id=billet.id
        )

    return render_billet_form(
        request,
        dossiers,
        responsables,
        employe
    )


# =========================================================
# DETAIL BILLET
# =========================================================


@login_required
@permission_required_metier('ticketing.view')
def billet_detail(request, billet_id):

    billet = get_object_or_404(
        get_accessible_billets(
            request.user
        ).select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'responsable',
            'responsable__user',
            'responsable__agence'
        ),
        id=billet_id
    )

    return render(
        request,
        'ticketing/billet_detail.html',
        {
            'billet': billet,

            'employe': getattr(
                request.user,
                'employe',
                None
            ),

            'global_access': has_global_agency_access(
                request.user
            ),
        }
    )


# =========================================================
# MODIFICATION BILLET
# =========================================================


@login_required
@permission_required_metier('ticketing.manage')
def billet_update(request, billet_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    billet = get_object_or_404(
        get_accessible_billets(
            request.user
        ).select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'responsable'
        ),
        id=billet_id
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).filter(
        type_service='BILLETTERIE'
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    responsables = get_accessible_responsables(
        request.user
    )

    if request.method == 'POST':

        ancien_statut = billet.statut
        ancien_responsable_id = billet.responsable_id
        ancien_prix = billet.prix
        ancien_dossier_id = billet.dossier_id

        dossier_id = request.POST.get(
            'dossier'
        )

        responsable_id = (
            request.POST.get(
                'responsable'
            )
            or None
        )

        type_billet = request.POST.get(
            'type_billet'
        )

        compagnie = (
            request.POST.get(
                'compagnie'
            )
            or ''
        ).strip()

        ville_depart = (
            request.POST.get(
                'ville_depart'
            )
            or ''
        ).strip()

        ville_arrivee = (
            request.POST.get(
                'ville_arrivee'
            )
            or ''
        ).strip()

        date_depart_raw = (
            request.POST.get(
                'date_depart'
            )
            or ''
        ).strip()

        date_retour_raw = (
            request.POST.get(
                'date_retour'
            )
            or ''
        ).strip()

        prix_raw = (
            request.POST.get(
                'prix'
            )
            or ''
        ).strip()

        statut = request.POST.get(
            'statut'
        )

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # RESPONSABLE
        # =================================================

        responsable = None

        if responsable_id:

            responsable = get_object_or_404(
                responsables,
                id=responsable_id
            )

        # =================================================
        # TYPE
        # =================================================

        if type_billet not in TYPES_BILLET_AUTORISES:

            messages.error(
                request,
                "Le type de billet est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in STATUTS_BILLET_AUTORISES:

            messages.error(
                request,
                "Le statut du billet est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        # =================================================
        # COMPAGNIE / VILLES
        # =================================================

        if not compagnie:

            messages.error(
                request,
                "La compagnie est obligatoire."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        if not ville_depart or not ville_arrivee:

            messages.error(
                request,
                (
                    "La ville de départ et la ville "
                    "d'arrivée sont obligatoires."
                )
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        # =================================================
        # DATE DE DEPART
        # =================================================

        if not date_depart_raw:

            messages.error(
                request,
                "La date de départ est obligatoire."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        date_depart = convertir_datetime(
            date_depart_raw
        )

        if date_depart is None:

            messages.error(
                request,
                "La date de départ est invalide."
            )

            return render_billet_form(
                request,
                dossiers,
                responsables,
                employe,
                billet
            )

        # =================================================
        # DATE DE RETOUR
        # =================================================

        date_retour = None

        if date_retour_raw:

            date_retour = convertir_datetime(
                date_retour_raw
            )

            if date_retour is None:

                messages.error(
                    request,
                    "La date de retour est invalide."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe,
                    billet
                )

            if date_retour < date_depart:

                messages.error(
                    request,
                    (
                        "La date de retour ne peut pas "
                        "être antérieure à la date de départ."
                    )
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe,
                    billet
                )

        # =================================================
        # PRIX
        # =================================================

        prix = None

        if prix_raw:

            try:

                prix = Decimal(
                    prix_raw
                )

            except InvalidOperation:

                messages.error(
                    request,
                    "Le prix du billet est invalide."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe,
                    billet
                )

            if prix < 0:

                messages.error(
                    request,
                    "Le prix ne peut pas être négatif."
                )

                return render_billet_form(
                    request,
                    dossiers,
                    responsables,
                    employe,
                    billet
                )

        # =================================================
        # UPDATE
        # =================================================

        billet.dossier = dossier
        billet.responsable = responsable
        billet.type_billet = type_billet
        billet.compagnie = compagnie

        billet.reference_reservation = (
            request.POST.get(
                'reference_reservation'
            )
            or ''
        ).strip() or None

        billet.ville_depart = ville_depart
        billet.ville_arrivee = ville_arrivee

        billet.date_depart = date_depart
        billet.date_retour = date_retour

        billet.prix = prix
        billet.statut = statut

        billet.commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        billet.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Modification d'un billet",
            module="Billetterie",
            objet_id=billet.id,
            description=(
                f"Billet modifié pour le dossier "
                f"{billet.dossier.numero_dossier}"
            )
        )

        # =================================================
        # STATUT
        # =================================================

        if ancien_statut != billet.statut:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de statut billet",
                module="Billetterie",
                objet_id=billet.id,
                description=(
                    f"Dossier "
                    f"{billet.dossier.numero_dossier} : "
                    f"{ancien_statut} → "
                    f"{billet.statut}"
                )
            )

        # =================================================
        # RESPONSABLE
        # =================================================

        if ancien_responsable_id != billet.responsable_id:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du responsable billetterie",
                module="Billetterie",
                objet_id=billet.id,
                description=(
                    f"Nouveau responsable : "
                    f"{billet.responsable if billet.responsable else 'Aucun'}"
                )
            )

        # =================================================
        # PRIX
        # =================================================

        if ancien_prix != billet.prix:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Modification du prix du billet",
                module="Billetterie",
                objet_id=billet.id,
                description=(
                    f"{ancien_prix if ancien_prix is not None else 0} MAD → "
                    f"{billet.prix if billet.prix is not None else 0} MAD"
                )
            )

        # =================================================
        # DOSSIER
        # =================================================

        if ancien_dossier_id != billet.dossier_id:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du dossier du billet",
                module="Billetterie",
                objet_id=billet.id,
                description=(
                    f"Nouveau dossier : "
                    f"{billet.dossier.numero_dossier}"
                )
            )

        messages.success(
            request,
            "Le billet a été modifié avec succès."
        )

        return redirect(
            'billet_detail',
            billet_id=billet.id
        )

    return render_billet_form(
        request,
        dossiers,
        responsables,
        employe,
        billet
    )