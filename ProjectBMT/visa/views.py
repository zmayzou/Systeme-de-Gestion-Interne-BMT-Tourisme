from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.decorators import permission_required_metier
from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from notifications.models import HistoriqueAction

from .models import Visa
from dossiers.models import Dossier
from accounts.models import Employe


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


def get_accessible_visas(user):
    visas = Visa.objects.all()

    if has_global_agency_access(user):
        return visas

    agence = get_user_agence(user)

    if not agence:
        return visas.none()

    return visas.filter(
        dossier__agence=agence
    )


def get_accessible_responsables(user):
    responsables = Employe.objects.filter(
        est_actif=True,
        role__nom='Responsable Visa'
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
# LISTE VISAS
# =========================================================


@login_required
@permission_required_metier('visa.view')
def visa_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    visas = get_accessible_visas(
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
        'visa/visa_list.html',
        {
            'visas': visas,
            'employe': employe,
            'global_access': has_global_agency_access(
                request.user
            ),
        }
    )


# =========================================================
# CREATION VISA
# =========================================================


@login_required
@permission_required_metier('visa.manage')
def visa_create(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).filter(
        type_service='VISA'
    ).exclude(
        visa__isnull=False
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

        pays_destination = (
            request.POST.get(
                'pays_destination'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or 'DOCUMENTS_MANQUANTS'
        )

        # =================================================
        # VALIDATIONS
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render(
                request,
                'visa/visa_form.html',
                {
                    'dossiers': dossiers,
                    'responsables': responsables,
                    'employe': employe,
                }
            )

        if not pays_destination:

            messages.error(
                request,
                "Le pays de destination est obligatoire."
            )

            return render(
                request,
                'visa/visa_form.html',
                {
                    'dossiers': dossiers,
                    'responsables': responsables,
                    'employe': employe,
                }
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        responsable = None

        if responsable_id:

            responsable = get_object_or_404(
                responsables,
                id=responsable_id
            )

        statuts_autorises = [
            'DOCUMENTS_MANQUANTS',
            'DOCUMENTS_COMPLETS',
            'DOSSIER_PRET',
            'DEPOSE',
            'EN_TRAITEMENT',
            'ACCEPTE',
            'REFUSE',
        ]

        if statut not in statuts_autorises:

            messages.error(
                request,
                "Le statut du visa est invalide."
            )

            return render(
                request,
                'visa/visa_form.html',
                {
                    'dossiers': dossiers,
                    'responsables': responsables,
                    'employe': employe,
                }
            )

        # =================================================
        # CREATION
        # =================================================

        visa = Visa.objects.create(
            dossier=dossier,
            responsable=responsable,
            pays_destination=pays_destination,
            type_visa=(
                request.POST.get(
                    'type_visa'
                )
                or None
            ),
            statut=statut,
            date_depot=(
                request.POST.get(
                    'date_depot'
                )
                or None
            ),
            date_rendez_vous=(
                request.POST.get(
                    'date_rendez_vous'
                )
                or None
            ),
            date_resultat=(
                request.POST.get(
                    'date_resultat'
                )
                or None
            ),
            numero_demande=(
                request.POST.get(
                    'numero_demande'
                )
                or None
            ),
            commentaire=(
                request.POST.get(
                    'commentaire'
                )
                or None
            ),
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Création d'une demande de visa",
            module="Visa",
            objet_id=visa.id,
            description=(
                f"Visa créé pour le dossier "
                f"{visa.dossier.numero_dossier} - "
                f"Destination : {visa.pays_destination} - "
                f"Agence : {visa.dossier.agence}"
            )
        )

        messages.success(
            request,
            "La demande de visa a été créée avec succès."
        )

        return redirect(
            'visa_detail',
            visa_id=visa.id
        )

    return render(
        request,
        'visa/visa_form.html',
        {
            'dossiers': dossiers,
            'responsables': responsables,
            'employe': employe,
        }
    )


# =========================================================
# DETAIL VISA
# =========================================================


@login_required
@permission_required_metier('visa.view')
def visa_detail(request, visa_id):

    visa = get_object_or_404(
        get_accessible_visas(
            request.user
        ).select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'responsable',
            'responsable__user',
            'responsable__agence'
        ),
        id=visa_id
    )

    return render(
        request,
        'visa/visa_detail.html',
        {
            'visa': visa,
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
# MODIFICATION VISA
# =========================================================


@login_required
@permission_required_metier('visa.manage')
def visa_update(request, visa_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    visa = get_object_or_404(
        get_accessible_visas(
            request.user
        ).select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'responsable'
        ),
        id=visa_id
    )

    responsables = get_accessible_responsables(
        request.user
    )

    if request.method == 'POST':

        ancien_statut = visa.statut
        ancien_responsable_id = (
            visa.responsable_id
        )

        responsable_id = (
            request.POST.get(
                'responsable'
            )
            or None
        )

        pays_destination = (
            request.POST.get(
                'pays_destination'
            )
            or ''
        ).strip()

        nouveau_statut = (
            request.POST.get(
                'statut'
            )
        )

        # =================================================
        # VALIDATIONS
        # =================================================

        if not pays_destination:

            messages.error(
                request,
                "Le pays de destination est obligatoire."
            )

            return render(
                request,
                'visa/visa_form.html',
                {
                    'visa': visa,
                    'responsables': responsables,
                    'employe': employe,
                }
            )

        statuts_autorises = [
            'DOCUMENTS_MANQUANTS',
            'DOCUMENTS_COMPLETS',
            'DOSSIER_PRET',
            'DEPOSE',
            'EN_TRAITEMENT',
            'ACCEPTE',
            'REFUSE',
        ]

        if nouveau_statut not in statuts_autorises:

            messages.error(
                request,
                "Le statut du visa est invalide."
            )

            return render(
                request,
                'visa/visa_form.html',
                {
                    'visa': visa,
                    'responsables': responsables,
                    'employe': employe,
                }
            )

        nouveau_responsable = None

        if responsable_id:

            nouveau_responsable = get_object_or_404(
                responsables,
                id=responsable_id
            )

        # =================================================
        # UPDATE
        # =================================================

        visa.responsable = nouveau_responsable
        visa.pays_destination = pays_destination

        visa.type_visa = (
            request.POST.get(
                'type_visa'
            )
            or None
        )

        visa.statut = nouveau_statut

        visa.date_depot = (
            request.POST.get(
                'date_depot'
            )
            or None
        )

        visa.date_rendez_vous = (
            request.POST.get(
                'date_rendez_vous'
            )
            or None
        )

        visa.date_resultat = (
            request.POST.get(
                'date_resultat'
            )
            or None
        )

        visa.numero_demande = (
            request.POST.get(
                'numero_demande'
            )
            or None
        )

        visa.commentaire = (
            request.POST.get(
                'commentaire'
            )
            or None
        )

        visa.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Modification d'une demande de visa",
            module="Visa",
            objet_id=visa.id,
            description=(
                f"Visa modifié pour le dossier "
                f"{visa.dossier.numero_dossier}"
            )
        )

        # =================================================
        # CHANGEMENT STATUT
        # =================================================

        if ancien_statut != visa.statut:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de statut visa",
                module="Visa",
                objet_id=visa.id,
                description=(
                    f"Dossier "
                    f"{visa.dossier.numero_dossier} : "
                    f"{ancien_statut} → "
                    f"{visa.statut}"
                )
            )

        # =================================================
        # CHANGEMENT RESPONSABLE
        # =================================================

        if (
            ancien_responsable_id
            != visa.responsable_id
        ):

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du responsable visa",
                module="Visa",
                objet_id=visa.id,
                description=(
                    f"Nouveau responsable : "
                    f"{visa.responsable if visa.responsable else 'Aucun'}"
                )
            )

        messages.success(
            request,
            "La demande de visa a été modifiée avec succès."
        )

        return redirect(
            'visa_detail',
            visa_id=visa.id
        )

    return render(
        request,
        'visa/visa_form.html',
        {
            'visa': visa,
            'responsables': responsables,
            'employe': employe,
        }
    )