from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from accounts.decorators import (
    permission_required_metier,
    has_metier_permission
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from notifications.models import (
    Notification,
    HistoriqueAction
)

from .models import Guide, MissionGuide
from accounts.models import Employe
from dossiers.models import Dossier


# =========================================================
# CONSTANTES
# =========================================================


STATUTS_MISSION_AUTORISES = [
    'PLANIFIEE',
    'EN_COURS',
    'TERMINEE',
    'ANNULEE',
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


def get_accessible_guides(user):

    guides = Guide.objects.all()

    if has_global_agency_access(user):
        return guides

    agence = get_user_agence(user)

    if not agence:
        return guides.none()

    return guides.filter(
        employe__agence=agence
    )


def get_accessible_missions_for_manager(user):

    missions = MissionGuide.objects.all()

    if has_global_agency_access(user):
        return missions

    agence = get_user_agence(user)

    if not agence:
        return missions.none()

    return missions.filter(
        dossier__agence=agence
    )


# =========================================================
# HELPER - DATETIME
# =========================================================


def convertir_datetime(valeur):
    """
    Convertit une valeur provenant d'un input datetime-local
    en objet datetime Django.
    """

    if not valeur:
        return None

    valeur = valeur.strip()

    date_obj = parse_datetime(
        valeur
    )

    if date_obj is None:
        return None

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
# HELPER - FORM MISSION
# =========================================================


def render_mission_form(
    request,
    guides,
    dossiers,
    employe,
    mission=None
):

    context = {
        'guides': guides,
        'dossiers': dossiers,
        'employe': employe,
    }

    if mission is not None:
        context['mission'] = mission

    return render(
        request,
        'guides/mission_form.html',
        context
    )


# =========================================================
# LISTE DES GUIDES
# =========================================================


@login_required
@permission_required_metier('missions.manage')
def guide_list(request):

    guides = get_accessible_guides(
        request.user
    ).select_related(
        'employe',
        'employe__user',
        'employe__agence',
        'employe__role'
    ).order_by(
        'employe__user__first_name',
        'employe__user__last_name',
        'employe__user__username'
    )

    return render(
        request,
        'guides/guide_list.html',
        {
            'guides': guides,

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
# CREATION PROFIL GUIDE
# =========================================================


@login_required
@permission_required_metier('missions.manage')
def guide_create(request):

    employe_connecte = getattr(
        request.user,
        'employe',
        None
    )

    employes = Employe.objects.filter(
        est_actif=True,
        role__nom='Guide',
        profil_guide__isnull=True
    ).select_related(
        'user',
        'agence',
        'role'
    )

    if not has_global_agency_access(
        request.user
    ):

        agence = get_user_agence(
            request.user
        )

        if agence:

            employes = employes.filter(
                agence=agence
            )

        else:

            employes = employes.none()

    if request.method == 'POST':

        employe_id = request.POST.get(
            'employe'
        )

        if not employe_id:

            messages.error(
                request,
                "Veuillez sélectionner un employé."
            )

            return render(
                request,
                'guides/guide_form.html',
                {
                    'employes': employes,
                    'employe': employe_connecte,
                }
            )

        employe_guide = get_object_or_404(
            employes,
            id=employe_id
        )

        guide = Guide.objects.create(
            employe=employe_guide,

            langues=(
                request.POST.get(
                    'langues'
                )
                or ''
            ).strip() or None,

            specialite=(
                request.POST.get(
                    'specialite'
                )
                or ''
            ).strip() or None,

            est_disponible=(
                request.POST.get(
                    'est_disponible'
                )
                == 'on'
            ),
        )

        HistoriqueAction.objects.create(
            employe=employe_connecte,
            action="Création d'un profil guide",
            module="Guides",
            objet_id=guide.id,
            description=(
                f"Profil guide créé : "
                f"{guide.employe} - "
                f"Agence : "
                f"{guide.employe.agence}"
            )
        )

        messages.success(
            request,
            "Le profil guide a été créé avec succès."
        )

        return redirect(
            'guide_list'
        )

    return render(
        request,
        'guides/guide_form.html',
        {
            'employes': employes,
            'employe': employe_connecte,
        }
    )


# =========================================================
# LISTE DES MISSIONS
# =========================================================


@login_required
@permission_required_metier('missions.view')
def mission_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_manage = has_metier_permission(
        request.user,
        'missions.manage'
    )

    missions = MissionGuide.objects.select_related(
        'guide',
        'guide__employe',
        'guide__employe__user',
        'guide__employe__agence',
        'dossier',
        'dossier__client',
        'dossier__agence'
    )

    # GLOBAL
    if has_global_agency_access(
        request.user
    ):

        pass

    # MANAGER LOCAL
    elif can_manage:

        agence = get_user_agence(
            request.user
        )

        if agence:

            missions = missions.filter(
                dossier__agence=agence
            )

        else:

            missions = missions.none()

    # GUIDE / EMPLOYE NORMAL
    elif employe:

        missions = missions.filter(
            guide__employe=employe
        )

    else:

        missions = missions.none()

    missions = missions.order_by(
        '-date_debut'
    )

    return render(
        request,
        'guides/mission_list.html',
        {
            'missions': missions,
            'employe': employe,
            'can_manage': can_manage,

            'global_access': has_global_agency_access(
                request.user
            ),
        }
    )


# =========================================================
# CREATION D'UNE MISSION
# =========================================================


@login_required
@permission_required_metier('missions.manage')
def mission_create(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    guides = get_accessible_guides(
        request.user
    ).filter(
        est_disponible=True,
        employe__est_actif=True
    ).select_related(
        'employe',
        'employe__user',
        'employe__agence',
        'employe__role'
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    if request.method == 'POST':

        guide_id = request.POST.get(
            'guide'
        )

        dossier_id = request.POST.get(
            'dossier'
        )

        lieu = (
            request.POST.get(
                'lieu'
            )
            or ''
        ).strip()

        date_debut_raw = (
            request.POST.get(
                'date_debut'
            )
            or ''
        ).strip()

        date_fin_raw = (
            request.POST.get(
                'date_fin'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or 'PLANIFIEE'
        )

        # =================================================
        # GUIDE
        # =================================================

        if not guide_id:

            messages.error(
                request,
                "Veuillez sélectionner un guide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        guide = get_object_or_404(
            guides,
            id=guide_id
        )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # AGENCY CONSISTENCY
        # =================================================

        if (
            guide.employe.agence_id
            != dossier.agence_id
        ):

            messages.error(
                request,
                (
                    "Le guide et le dossier doivent "
                    "appartenir à la même agence."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        # =================================================
        # LIEU
        # =================================================

        if not lieu:

            messages.error(
                request,
                "Le lieu de la mission est obligatoire."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        # =================================================
        # DATES
        # =================================================

        if not date_debut_raw or not date_fin_raw:

            messages.error(
                request,
                (
                    "Les dates de début et de fin "
                    "sont obligatoires."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        date_debut = convertir_datetime(
            date_debut_raw
        )

        date_fin = convertir_datetime(
            date_fin_raw
        )

        if date_debut is None:

            messages.error(
                request,
                "La date de début est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        if date_fin is None:

            messages.error(
                request,
                "La date de fin est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        if date_fin < date_debut:

            messages.error(
                request,
                (
                    "La date de fin ne peut pas être "
                    "antérieure à la date de début."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in STATUTS_MISSION_AUTORISES:

            messages.error(
                request,
                "Le statut de la mission est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe
            )

        # =================================================
        # CREATION
        # =================================================

        mission = MissionGuide.objects.create(
            guide=guide,
            dossier=dossier,
            lieu=lieu,
            date_debut=date_debut,
            date_fin=date_fin,
            statut=statut,

            commentaire=(
                request.POST.get(
                    'commentaire'
                )
                or ''
            ).strip() or None,
        )

        # =================================================
        # NOTIFICATION
        # =================================================

        Notification.objects.create(
            employe=mission.guide.employe,
            titre="Nouvelle mission",
            message=(
                f"Une nouvelle mission vous a été "
                f"assignée à {mission.lieu}."
            )
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Création d'une mission",
            module="Missions",
            objet_id=mission.id,
            description=(
                f"Mission créée : "
                f"{mission.lieu} - "
                f"Guide : {mission.guide} - "
                f"Dossier : "
                f"{mission.dossier.numero_dossier} - "
                f"Agence : "
                f"{mission.dossier.agence}"
            )
        )

        HistoriqueAction.objects.create(
            employe=employe,
            action="Assignation d'une mission",
            module="Missions",
            objet_id=mission.id,
            description=(
                f"Mission {mission.lieu} "
                f"assignée à {mission.guide}"
            )
        )

        messages.success(
            request,
            (
                "La mission a été créée "
                "et le guide a été notifié."
            )
        )

        return redirect(
            'mission_detail',
            mission_id=mission.id
        )

    return render_mission_form(
        request,
        guides,
        dossiers,
        employe
    )


# =========================================================
# DETAIL MISSION
# =========================================================


@login_required
@permission_required_metier('missions.view')
def mission_detail(request, mission_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_manage = has_metier_permission(
        request.user,
        'missions.manage'
    )

    missions = MissionGuide.objects.select_related(
        'guide',
        'guide__employe',
        'guide__employe__user',
        'guide__employe__agence',
        'dossier',
        'dossier__client',
        'dossier__agence'
    )

    if has_global_agency_access(
        request.user
    ):

        pass

    elif can_manage:

        agence = get_user_agence(
            request.user
        )

        if agence:

            missions = missions.filter(
                dossier__agence=agence
            )

        else:

            missions = missions.none()

    elif employe:

        missions = missions.filter(
            guide__employe=employe
        )

    else:

        missions = missions.none()

    mission = get_object_or_404(
        missions,
        id=mission_id
    )

    return render(
        request,
        'guides/mission_detail.html',
        {
            'mission': mission,
            'employe': employe,
            'can_manage': can_manage,

            'global_access': has_global_agency_access(
                request.user
            ),
        }
    )


# =========================================================
# MODIFICATION COMPLETE MISSION
# =========================================================


@login_required
@permission_required_metier('missions.manage')
def mission_update(request, mission_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    mission = get_object_or_404(
        get_accessible_missions_for_manager(
            request.user
        ).select_related(
            'guide',
            'guide__employe',
            'guide__employe__agence',
            'dossier',
            'dossier__agence'
        ),
        id=mission_id
    )

    guides = get_accessible_guides(
        request.user
    ).filter(
        employe__est_actif=True
    ).select_related(
        'employe',
        'employe__user',
        'employe__agence',
        'employe__role'
    )

    # Le guide actuel reste accessible
    # même s'il est devenu indisponible.
    guides = (
        Guide.objects.filter(
            id__in=guides.values('id')
        )
        |
        Guide.objects.filter(
            id=mission.guide_id
        )
    )

    guides = guides.select_related(
        'employe',
        'employe__user',
        'employe__agence',
        'employe__role'
    ).distinct()

    dossiers = get_accessible_dossiers(
        request.user
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    if request.method == 'POST':

        ancien_statut = mission.statut
        ancien_guide_id = mission.guide_id
        ancien_dossier_id = mission.dossier_id
        ancien_lieu = mission.lieu
        ancienne_date_debut = mission.date_debut
        ancienne_date_fin = mission.date_fin

        guide_id = request.POST.get(
            'guide'
        )

        dossier_id = request.POST.get(
            'dossier'
        )

        lieu = (
            request.POST.get(
                'lieu'
            )
            or ''
        ).strip()

        date_debut_raw = (
            request.POST.get(
                'date_debut'
            )
            or ''
        ).strip()

        date_fin_raw = (
            request.POST.get(
                'date_fin'
            )
            or ''
        ).strip()

        statut = request.POST.get(
            'statut'
        )

        # =================================================
        # GUIDE
        # =================================================

        if not guide_id:

            messages.error(
                request,
                "Veuillez sélectionner un guide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        guide = get_object_or_404(
            guides,
            id=guide_id
        )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # AGENCY CONSISTENCY
        # =================================================

        if (
            guide.employe.agence_id
            != dossier.agence_id
        ):

            messages.error(
                request,
                (
                    "Le guide et le dossier doivent "
                    "appartenir à la même agence."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        # =================================================
        # LIEU
        # =================================================

        if not lieu:

            messages.error(
                request,
                "Le lieu de la mission est obligatoire."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        # =================================================
        # DATES
        # =================================================

        if not date_debut_raw or not date_fin_raw:

            messages.error(
                request,
                (
                    "Les dates de début et de fin "
                    "sont obligatoires."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        date_debut = convertir_datetime(
            date_debut_raw
        )

        date_fin = convertir_datetime(
            date_fin_raw
        )

        if date_debut is None:

            messages.error(
                request,
                "La date de début est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        if date_fin is None:

            messages.error(
                request,
                "La date de fin est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        if date_fin < date_debut:

            messages.error(
                request,
                (
                    "La date de fin ne peut pas être "
                    "antérieure à la date de début."
                )
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in STATUTS_MISSION_AUTORISES:

            messages.error(
                request,
                "Le statut de la mission est invalide."
            )

            return render_mission_form(
                request,
                guides,
                dossiers,
                employe,
                mission
            )

        # =================================================
        # UPDATE
        # =================================================

        mission.guide = guide
        mission.dossier = dossier
        mission.lieu = lieu
        mission.date_debut = date_debut
        mission.date_fin = date_fin
        mission.statut = statut

        mission.commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        mission.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Modification d'une mission",
            module="Missions",
            objet_id=mission.id,
            description=(
                f"Mission modifiée : "
                f"{mission.lieu}"
            )
        )

        # =================================================
        # GUIDE CHANGE
        # =================================================

        if ancien_guide_id != mission.guide_id:

            Notification.objects.create(
                employe=mission.guide.employe,
                titre="Nouvelle mission assignée",
                message=(
                    f"La mission à {mission.lieu} "
                    f"vous a été assignée."
                )
            )

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du guide",
                module="Missions",
                objet_id=mission.id,
                description=(
                    f"Nouveau guide : "
                    f"{mission.guide}"
                )
            )

        # =================================================
        # STATUT
        # =================================================

        if ancien_statut != mission.statut:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de statut mission",
                module="Missions",
                objet_id=mission.id,
                description=(
                    f"{ancien_statut} → "
                    f"{mission.statut}"
                )
            )

        # =================================================
        # DOSSIER
        # =================================================

        if ancien_dossier_id != mission.dossier_id:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du dossier mission",
                module="Missions",
                objet_id=mission.id,
                description=(
                    f"Nouveau dossier : "
                    f"{mission.dossier.numero_dossier}"
                )
            )

        # =================================================
        # LIEU
        # =================================================

        if ancien_lieu != mission.lieu:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du lieu mission",
                module="Missions",
                objet_id=mission.id,
                description=(
                    f"{ancien_lieu} → "
                    f"{mission.lieu}"
                )
            )

        # =================================================
        # DATES
        # =================================================

        if (
            ancienne_date_debut != mission.date_debut
            or ancienne_date_fin != mission.date_fin
        ):

            HistoriqueAction.objects.create(
                employe=employe,
                action="Modification des dates mission",
                module="Missions",
                objet_id=mission.id,
                description=(
                    f"Dates de la mission "
                    f"{mission.lieu} modifiées."
                )
            )

        messages.success(
            request,
            "La mission a été modifiée avec succès."
        )

        return redirect(
            'mission_detail',
            mission_id=mission.id
        )

    return render_mission_form(
        request,
        guides,
        dossiers,
        employe,
        mission
    )


# =========================================================
# MISE A JOUR STATUT
# =========================================================


@login_required
@permission_required_metier('missions.update_status')
def mission_update_status(request, mission_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_manage = has_metier_permission(
        request.user,
        'missions.manage'
    )

    missions = MissionGuide.objects.select_related(
        'guide',
        'guide__employe',
        'dossier',
        'dossier__agence'
    )

    if has_global_agency_access(
        request.user
    ):

        pass

    elif can_manage:

        agence = get_user_agence(
            request.user
        )

        if agence:

            missions = missions.filter(
                dossier__agence=agence
            )

        else:

            missions = missions.none()

    elif employe:

        missions = missions.filter(
            guide__employe=employe
        )

    else:

        missions = missions.none()

    mission = get_object_or_404(
        missions,
        id=mission_id
    )

    if request.method == 'POST':

        nouveau_statut = request.POST.get(
            'statut'
        )

        if nouveau_statut not in STATUTS_MISSION_AUTORISES:

            messages.error(
                request,
                "Statut de mission invalide."
            )

            return redirect(
                'mission_detail',
                mission_id=mission.id
            )

        ancien_statut = mission.statut

        if ancien_statut == nouveau_statut:

            messages.info(
                request,
                "Le statut de la mission n'a pas changé."
            )

            return redirect(
                'mission_detail',
                mission_id=mission.id
            )

        mission.statut = nouveau_statut

        mission.save(
            update_fields=[
                'statut'
            ]
        )

        HistoriqueAction.objects.create(
            employe=employe,
            action="Changement de statut mission",
            module="Missions",
            objet_id=mission.id,
            description=(
                f"Mission {mission.lieu} : "
                f"{ancien_statut} → "
                f"{mission.statut}"
            )
        )

        messages.success(
            request,
            (
                "Le statut de la mission "
                "a été modifié avec succès."
            )
        )

        return redirect(
            'mission_detail',
            mission_id=mission.id
        )

    return render(
        request,
        'guides/mission_status_form.html',
        {
            'mission': mission,
            'employe': employe,
            'can_manage': can_manage,
        }
    )