from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.decorators import (
    permission_required_metier,
    has_metier_permission
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from .models import Tache
from dossiers.models import Dossier
from accounts.models import Employe
from notifications.models import Notification, HistoriqueAction


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


def get_accessible_employes(user):
    employes = Employe.objects.filter(
        est_actif=True
    )

    if has_global_agency_access(user):
        return employes

    agence = get_user_agence(user)

    if not agence:
        return employes.none()

    return employes.filter(
        agence=agence
    )


def get_accessible_tasks_for_manager(user):
    taches = Tache.objects.all()

    if has_global_agency_access(user):
        return taches

    agence = get_user_agence(user)

    if not agence:
        return taches.none()

    return taches.filter(
        dossier__agence=agence
    )


def get_accessible_tasks(user):
    """
    Global:
        toutes les tâches.

    Utilisateur avec tasks.assign:
        tâches de son agence.

    Employé normal:
        uniquement ses propres tâches.
    """

    taches = Tache.objects.all()

    if has_global_agency_access(user):
        return taches

    employe = getattr(
        user,
        'employe',
        None
    )

    if not employe:
        return taches.none()

    can_assign = has_metier_permission(
        user,
        'tasks.assign'
    )

    if can_assign:
        if not employe.agence:
            return taches.none()

        return taches.filter(
            dossier__agence=employe.agence
        )

    return taches.filter(
        responsable=employe
    )


# =========================================================
# LISTE DES TACHES
# =========================================================


@login_required
@permission_required_metier('tasks.view')
def task_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_assign = has_metier_permission(
        request.user,
        'tasks.assign'
    )

    taches = get_accessible_tasks(
        request.user
    ).select_related(
        'dossier',
        'dossier__client',
        'dossier__agence',
        'responsable',
        'responsable__user',
        'responsable__agence',
        'cree_par',
        'cree_par__user'
    ).order_by(
        '-date_creation'
    )

    return render(
        request,
        'tasks/task_list.html',
        {
            'taches': taches,
            'employe': employe,
            'can_assign': can_assign,
            'global_access': (
                has_global_agency_access(
                    request.user
                )
            ),
        }
    )


# =========================================================
# CREATION D'UNE TACHE
# =========================================================


@login_required
@permission_required_metier('tasks.create')
def task_create(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_assign = has_metier_permission(
        request.user,
        'tasks.assign'
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    if can_assign:

        employes = get_accessible_employes(
            request.user
        ).select_related(
            'user',
            'role',
            'agence'
        ).order_by(
            'user__first_name',
            'user__last_name',
            'user__username'
        )

    else:
        employes = Employe.objects.none()

    if request.method == 'POST':

        dossier_id = request.POST.get(
            'dossier'
        )

        titre = (
            request.POST.get(
                'titre'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or 'A_FAIRE'
        )

        priorite = (
            request.POST.get(
                'priorite'
            )
            or 'MOYENNE'
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
                'tasks/task_form.html',
                {
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        # Sécurité :
        # impossible d'utiliser un dossier
        # d'une autre agence via POST manuel.

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        if not titre:

            messages.error(
                request,
                "Le titre de la tâche est obligatoire."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        statuts_autorises = [
            'A_FAIRE',
            'EN_COURS',
            'EN_ATTENTE',
            'TERMINEE',
            'ANNULEE',
        ]

        if statut not in statuts_autorises:

            messages.error(
                request,
                "Le statut de la tâche est invalide."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        priorites_autorisees = [
            'FAIBLE',
            'MOYENNE',
            'HAUTE',
            'URGENTE',
        ]

        if priorite not in priorites_autorisees:

            messages.error(
                request,
                "La priorité est invalide."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        # =================================================
        # RESPONSABLE
        # =================================================

        responsable = None

        if can_assign:

            responsable_id = (
                request.POST.get(
                    'responsable'
                )
                or None
            )

            if responsable_id:
                responsable = get_object_or_404(
                    employes,
                    id=responsable_id
                )

        else:
            responsable = employe

        # =================================================
        # CREATION
        # =================================================

        tache = Tache.objects.create(
            dossier=dossier,
            responsable=responsable,
            cree_par=employe,
            titre=titre,
            description=(
                request.POST.get(
                    'description'
                )
                or None
            ),
            statut=statut,
            priorite=priorite,
            date_echeance=(
                request.POST.get(
                    'date_echeance'
                )
                or None
            ),
        )

        # =================================================
        # NOTIFICATION
        # =================================================

        if tache.responsable:

            Notification.objects.create(
                employe=tache.responsable,
                titre="Nouvelle tâche",
                message=(
                    f"Une nouvelle tâche vous a été "
                    f"assignée : {tache.titre}."
                )
            )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Création d'une tâche",
            module="Tâches",
            objet_id=tache.id,
            description=(
                f"Tâche créée : "
                f"{tache.titre} - "
                f"Dossier "
                f"{tache.dossier.numero_dossier} - "
                f"Agence : "
                f"{tache.dossier.agence}"
            )
        )

        if tache.responsable:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Assignation d'une tâche",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"Tâche {tache.titre} "
                    f"assignée à "
                    f"{tache.responsable}"
                )
            )

        messages.success(
            request,
            "La tâche a été créée avec succès."
        )

        return redirect(
            'task_detail',
            task_id=tache.id
        )

    return render(
        request,
        'tasks/task_form.html',
        {
            'dossiers': dossiers,
            'employes': employes,
            'employe': employe,
            'can_assign': can_assign,
        }
    )


# =========================================================
# DETAIL D'UNE TACHE
# =========================================================


@login_required
@permission_required_metier('tasks.view')
def task_detail(request, task_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_assign = has_metier_permission(
        request.user,
        'tasks.assign'
    )

    tache = get_object_or_404(
        get_accessible_tasks(
            request.user
        ).select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'responsable',
            'responsable__user',
            'responsable__agence',
            'cree_par',
            'cree_par__user'
        ),
        id=task_id
    )

    return render(
        request,
        'tasks/task_detail.html',
        {
            'tache': tache,
            'employe': employe,
            'can_assign': can_assign,
            'global_access': (
                has_global_agency_access(
                    request.user
                )
            ),
        }
    )


# =========================================================
# MODIFICATION D'UNE TACHE
# =========================================================


@login_required
@permission_required_metier('tasks.update')
def task_update(request, task_id):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    can_assign = has_metier_permission(
        request.user,
        'tasks.assign'
    )

    # On récupère uniquement une tâche
    # que l'utilisateur a le droit de gérer.

    tache = get_object_or_404(
        get_accessible_tasks(
            request.user
        ).select_related(
            'dossier',
            'dossier__agence',
            'responsable',
            'cree_par'
        ),
        id=task_id
    )

    dossiers = get_accessible_dossiers(
        request.user
    ).select_related(
        'client',
        'agence'
    ).order_by(
        '-date_creation'
    )

    if can_assign:

        employes = get_accessible_employes(
            request.user
        ).select_related(
            'user',
            'role',
            'agence'
        ).order_by(
            'user__first_name',
            'user__last_name',
            'user__username'
        )

    else:
        employes = Employe.objects.none()

    if request.method == 'POST':

        ancien_responsable_id = (
            tache.responsable_id
        )

        ancien_statut = tache.statut
        ancienne_priorite = tache.priorite
        ancien_dossier_id = tache.dossier_id
        ancien_titre = tache.titre

        dossier_id = request.POST.get(
            'dossier'
        )

        titre = (
            request.POST.get(
                'titre'
            )
            or ''
        ).strip()

        statut = request.POST.get(
            'statut'
        )

        priorite = request.POST.get(
            'priorite'
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
                'tasks/task_form.html',
                {
                    'tache': tache,
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        if not titre:

            messages.error(
                request,
                "Le titre de la tâche est obligatoire."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'tache': tache,
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        statuts_autorises = [
            'A_FAIRE',
            'EN_COURS',
            'EN_ATTENTE',
            'TERMINEE',
            'ANNULEE',
        ]

        if statut not in statuts_autorises:

            messages.error(
                request,
                "Le statut de la tâche est invalide."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'tache': tache,
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        priorites_autorisees = [
            'FAIBLE',
            'MOYENNE',
            'HAUTE',
            'URGENTE',
        ]

        if priorite not in priorites_autorisees:

            messages.error(
                request,
                "La priorité est invalide."
            )

            return render(
                request,
                'tasks/task_form.html',
                {
                    'tache': tache,
                    'dossiers': dossiers,
                    'employes': employes,
                    'employe': employe,
                    'can_assign': can_assign,
                }
            )

        # =================================================
        # RESPONSABLE
        # =================================================

        nouveau_responsable = (
            tache.responsable
        )

        if can_assign:

            responsable_id = (
                request.POST.get(
                    'responsable'
                )
                or None
            )

            if responsable_id:

                nouveau_responsable = (
                    get_object_or_404(
                        employes,
                        id=responsable_id
                    )
                )

            else:
                nouveau_responsable = None

        # =================================================
        # MISE A JOUR
        # =================================================

        tache.dossier = dossier
        tache.titre = titre

        tache.description = (
            request.POST.get(
                'description'
            )
            or None
        )

        tache.statut = statut
        tache.priorite = priorite

        tache.date_echeance = (
            request.POST.get(
                'date_echeance'
            )
            or None
        )

        if can_assign:
            tache.responsable = (
                nouveau_responsable
            )

        tache.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(
            employe=employe,
            action="Modification d'une tâche",
            module="Tâches",
            objet_id=tache.id,
            description=(
                f"Tâche modifiée : "
                f"{tache.titre}"
            )
        )

        # =================================================
        # CHANGEMENT RESPONSABLE
        # =================================================

        if (
            tache.responsable_id
            != ancien_responsable_id
        ):

            if tache.responsable:

                Notification.objects.create(
                    employe=tache.responsable,
                    titre="Nouvelle tâche assignée",
                    message=(
                        f"La tâche « {tache.titre} » "
                        f"vous a été assignée."
                    )
                )

                nouveau_responsable_texte = str(
                    tache.responsable
                )

            else:

                nouveau_responsable_texte = (
                    "Aucun responsable"
                )

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de responsable",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"Nouveau responsable : "
                    f"{nouveau_responsable_texte}"
                )
            )

        # =================================================
        # CHANGEMENT STATUT
        # =================================================

        if ancien_statut != tache.statut:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de statut tâche",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"{ancien_statut} → "
                    f"{tache.statut}"
                )
            )

        # =================================================
        # CHANGEMENT PRIORITE
        # =================================================

        if (
            ancienne_priorite
            != tache.priorite
        ):

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement de priorité",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"{ancienne_priorite} → "
                    f"{tache.priorite}"
                )
            )

        # =================================================
        # CHANGEMENT DOSSIER
        # =================================================

        if (
            ancien_dossier_id
            != tache.dossier_id
        ):

            HistoriqueAction.objects.create(
                employe=employe,
                action="Changement du dossier de la tâche",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"Nouveau dossier : "
                    f"{tache.dossier.numero_dossier}"
                )
            )

        # =================================================
        # CHANGEMENT TITRE
        # =================================================

        if ancien_titre != tache.titre:

            HistoriqueAction.objects.create(
                employe=employe,
                action="Modification du titre de la tâche",
                module="Tâches",
                objet_id=tache.id,
                description=(
                    f"{ancien_titre} → "
                    f"{tache.titre}"
                )
            )

        messages.success(
            request,
            "La tâche a été modifiée avec succès."
        )

        return redirect(
            'task_detail',
            task_id=tache.id
        )

    return render(
        request,
        'tasks/task_form.html',
        {
            'tache': tache,
            'dossiers': dossiers,
            'employes': employes,
            'employe': employe,
            'can_assign': can_assign,
        }
    )