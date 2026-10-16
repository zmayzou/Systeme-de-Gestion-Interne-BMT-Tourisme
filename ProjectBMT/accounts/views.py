from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST

from accounts.decorators import (
    permission_required_metier,
    has_metier_permission
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from accounts.models import (
    Employe,
    Role,
    PermissionMetier
)

from agencies.models import Agence

from clients.models import Client
from dossiers.models import Dossier
from tasks.models import Tache
from payments.models import Paiement
from visa.models import Visa
from ticketing.models import Billet
from guides.models import MissionGuide
from notifications.models import Notification


# =========================================================
# CONSTANTES
# =========================================================

GLOBAL_ROLE_NAMES = [
    'Administrateur',
    'Directeur',
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


def get_accessible_employees(user):

    employes = Employe.objects.all()

    if has_global_agency_access(user):
        return employes

    agence = get_user_agence(user)

    if not agence:
        return employes.none()

    return employes.filter(
        agence=agence
    )


def get_accessible_payments(user):

    paiements = Paiement.objects.all()

    if has_global_agency_access(user):
        return paiements

    agence = get_user_agence(user)

    if not agence:
        return paiements.none()

    return paiements.filter(
        dossier__agence=agence
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


# =========================================================
# HELPERS - ROLES / PERMISSIONS
# =========================================================


def get_assignable_roles(user):

    roles = Role.objects.all()

    if has_global_agency_access(user):

        return roles.order_by(
            'nom'
        )

    return roles.exclude(
        nom__in=GLOBAL_ROLE_NAMES
    ).order_by(
        'nom'
    )


def get_assignable_permissions(user):

    permissions = PermissionMetier.objects.all()

    if has_global_agency_access(user):

        return permissions.order_by(
            'nom'
        )

    employe = getattr(
        user,
        'employe',
        None
    )

    if not employe:

        return permissions.none()

    permission_ids = set(
        employe.permissions_metier
        .values_list(
            'id',
            flat=True
        )
    )

    if employe.role:

        permission_ids.update(
            employe.role.permissions
            .values_list(
                'id',
                flat=True
            )
        )

    return PermissionMetier.objects.filter(
        id__in=permission_ids
    ).order_by(
        'nom'
    )


# =========================================================
# AUTHENTIFICATION
# =========================================================


def login_view(request):

    if request.user.is_authenticated:

        return redirect(
            'dashboard'
        )

    if request.method == 'POST':

        username = request.POST.get(
            'username'
        )

        password = request.POST.get(
            'password'
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            employe = getattr(
                user,
                'employe',
                None
            )

            if (
                employe
                and not employe.est_actif
            ):

                messages.error(
                    request,
                    "Votre compte employé est désactivé."
                )

                return render(
                    request,
                    'accounts/login.html'
                )

            login(
                request,
                user
            )

            return redirect(
                'dashboard'
            )

        messages.error(
            request,
            "Nom d'utilisateur ou mot de passe incorrect."
        )

    return render(
        request,
        'accounts/login.html'
    )


# =========================================================
# DASHBOARD
# =========================================================


@login_required
def dashboard_view(request):

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

    context = {

        'employe': employe,
        'global_access': global_access,
        'agence': agence,

        'can_clients': has_metier_permission(
            request.user,
            'clients.view'
        ),

        'can_dossiers': has_metier_permission(
            request.user,
            'dossiers.view'
        ),

        'can_tasks': has_metier_permission(
            request.user,
            'tasks.view'
        ),

        'can_payments': has_metier_permission(
            request.user,
            'payments.view'
        ),

        'can_visa': has_metier_permission(
            request.user,
            'visa.view'
        ),

        'can_ticketing': has_metier_permission(
            request.user,
            'ticketing.view'
        ),

        'can_missions': has_metier_permission(
            request.user,
            'missions.view'
        ),
    }

    # =====================================================
    # CLIENTS
    # =====================================================

    if context['can_clients']:

        if global_access:

            clients = Client.objects.all()

        elif agence:

            clients = Client.objects.filter(
                agence=agence
            )

        else:

            clients = Client.objects.none()

        context['total_clients'] = (
            clients.count()
        )

    # =====================================================
    # DOSSIERS
    # =====================================================

    if context['can_dossiers']:

        dossiers = get_accessible_dossiers(
            request.user
        )

        context['total_dossiers'] = (
            dossiers.count()
        )

        context['dossiers_en_cours'] = (
            dossiers.filter(
                statut='EN_COURS'
            ).count()
        )

        context['dossiers_termines'] = (
            dossiers.filter(
                statut='TERMINE'
            ).count()
        )

        context['dossiers_bloques'] = (
            dossiers.filter(
                statut='BLOQUE'
            ).count()
        )

        context['derniers_dossiers'] = (
            dossiers
            .select_related(
                'client',
                'agence'
            )
            .order_by(
                '-date_creation'
            )[:5]
        )

    # =====================================================
    # TACHES
    # =====================================================

    if context['can_tasks']:

        can_assign = has_metier_permission(
            request.user,
            'tasks.assign'
        )

        taches = Tache.objects.all()

        if global_access:

            pass

        elif can_assign and agence:

            taches = taches.filter(
                dossier__agence=agence
            )

        elif employe:

            taches = taches.filter(
                responsable=employe
            )

        else:

            taches = taches.none()

        context['total_taches'] = (
            taches.count()
        )

        context['taches_a_faire'] = (
            taches.filter(
                statut='A_FAIRE'
            ).count()
        )

        context['taches_en_cours'] = (
            taches.filter(
                statut='EN_COURS'
            ).count()
        )

        context['taches_terminees'] = (
            taches.filter(
                statut='TERMINEE'
            ).count()
        )

        context['dernieres_taches'] = (
            taches
            .select_related(
                'dossier',
                'dossier__agence',
                'responsable',
                'responsable__user'
            )
            .order_by(
                '-date_creation'
            )[:5]
        )

    # =====================================================
    # PAIEMENTS
    # =====================================================

    if context['can_payments']:

        paiements = get_accessible_payments(
            request.user
        )

        context['total_paiements'] = (
            paiements.count()
        )

    # =====================================================
    # VISA
    # =====================================================

    if context['can_visa']:

        visas = get_accessible_visas(
            request.user
        )

        context['total_visas'] = (
            visas.count()
        )

        context['visas_en_traitement'] = (
            visas.filter(
                statut='EN_TRAITEMENT'
            ).count()
        )

        context['visas_acceptes'] = (
            visas.filter(
                statut='ACCEPTE'
            ).count()
        )

    # =====================================================
    # BILLETTERIE
    # =====================================================

    if context['can_ticketing']:

        billets = get_accessible_billets(
            request.user
        )

        context['total_billets'] = (
            billets.count()
        )

        context['billets_emis'] = (
            billets.filter(
                statut='BILLET_EMIS'
            ).count()
        )

    # =====================================================
    # MISSIONS GUIDES
    # =====================================================

    if context['can_missions']:

        can_manage_missions = (
            has_metier_permission(
                request.user,
                'missions.manage'
            )
        )

        missions = MissionGuide.objects.all()

        if global_access:

            pass

        elif can_manage_missions and agence:

            missions = missions.filter(
                dossier__agence=agence
            )

        elif employe:

            missions = missions.filter(
                guide__employe=employe
            )

        else:

            missions = missions.none()

        context['total_missions'] = (
            missions.count()
        )

        context['missions_en_cours'] = (
            missions.filter(
                statut='EN_COURS'
            ).count()
        )

    # =====================================================
    # NOTIFICATIONS
    # =====================================================

    if employe:

        context['dernieres_notifications'] = (
            Notification.objects
            .filter(
                employe=employe
            )
            .order_by(
                '-date_creation'
            )[:5]
        )

    else:

        context[
            'dernieres_notifications'
        ] = []

    return render(
        request,
        'accounts/dashboard.html',
        context
    )


# =========================================================
# LOGOUT
# =========================================================


def logout_view(request):

    logout(
        request
    )

    return redirect(
        'login'
    )


# =========================================================
# EMPLOYES - LISTE
# =========================================================


@login_required
@permission_required_metier('employees.view')
def employee_list(request):

    employes = (
        get_accessible_employees(
            request.user
        )
        .select_related(
            'user',
            'role',
            'agence'
        )
        .prefetch_related(
            'permissions_metier'
        )
        .order_by(
            'user__first_name',
            'user__last_name',
            'user__username'
        )
    )

    return render(
        request,
        'accounts/employee_list.html',
        {
            'employes': employes,

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
# EMPLOYES - CREATION
# =========================================================


@login_required
@permission_required_metier('employees.manage')
def employee_create(request):

    employe_connecte = getattr(
        request.user,
        'employe',
        None
    )

    global_access = (
        has_global_agency_access(
            request.user
        )
    )

    agence_connectee = get_user_agence(
        request.user
    )

    # =====================================================
    # AGENCES ACCESSIBLES
    # =====================================================

    if global_access:

        agences = Agence.objects.filter(
            est_active=True
        ).order_by(
            'nom'
        )

    elif agence_connectee:

        agences = Agence.objects.filter(
            id=agence_connectee.id,
            est_active=True
        )

    else:

        agences = Agence.objects.none()

    # =====================================================
    # ROLES / PERMISSIONS AUTORISES
    # =====================================================

    roles = get_assignable_roles(
        request.user
    )

    permissions = get_assignable_permissions(
        request.user
    )

    if request.method == 'POST':

        username = (
            request.POST.get(
                'username'
            )
            or ''
        ).strip()

        password = (
            request.POST.get(
                'password'
            )
            or ''
        )

        first_name = (
            request.POST.get(
                'first_name'
            )
            or ''
        ).strip()

        last_name = (
            request.POST.get(
                'last_name'
            )
            or ''
        ).strip()

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip()

        role_id = (
            request.POST.get(
                'role'
            )
            or None
        )

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip() or None

        poste = (
            request.POST.get(
                'poste'
            )
            or ''
        ).strip() or None

        date_embauche = (
            request.POST.get(
                'date_embauche'
            )
            or None
        )

        permission_ids = (
            request.POST.getlist(
                'permissions_metier'
            )
        )

        # =================================================
        # VALIDATION USER
        # =================================================

        if not username:

            messages.error(
                request,
                "Le nom d'utilisateur est obligatoire."
            )

            return render(
                request,
                'accounts/employee_form.html',
                {
                    'agences': agences,
                    'roles': roles,
                    'permissions': permissions,
                    'employe': employe_connecte,
                    'global_access': global_access,
                }
            )

        if not password:

            messages.error(
                request,
                "Le mot de passe est obligatoire."
            )

            return render(
                request,
                'accounts/employee_form.html',
                {
                    'agences': agences,
                    'roles': roles,
                    'permissions': permissions,
                    'employe': employe_connecte,
                    'global_access': global_access,
                }
            )

        if User.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                "Ce nom d'utilisateur existe déjà."
            )

            return render(
                request,
                'accounts/employee_form.html',
                {
                    'agences': agences,
                    'roles': roles,
                    'permissions': permissions,
                    'employe': employe_connecte,
                    'global_access': global_access,
                }
            )

        # =================================================
        # AGENCE
        # =================================================

        if global_access:

            agence_id = (
                request.POST.get(
                    'agence'
                )
                or None
            )

            agence_employee = None

            if agence_id:

                agence_employee = (
                    get_object_or_404(
                        agences,
                        id=agence_id
                    )
                )

        else:

            if not agence_connectee:

                messages.error(
                    request,
                    (
                        "Votre compte n'est associé "
                        "à aucune agence."
                    )
                )

                return redirect(
                    'employee_list'
                )

            agence_employee = (
                agence_connectee
            )

        # =================================================
        # ROLE
        # =================================================

        role = None

        if role_id:

            role = get_object_or_404(
                roles,
                id=role_id
            )

        # =================================================
        # CREATION USER
        # =================================================

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            email=email
        )

        # =================================================
        # CREATION EMPLOYE
        # =================================================

        nouveau_employe = (
            Employe.objects.create(
                user=user,
                agence=agence_employee,
                role=role,
                telephone=telephone,
                poste=poste,
                date_embauche=date_embauche,
                est_actif=True
            )
        )

        # =================================================
        # PERMISSIONS
        # =================================================

        if permission_ids:

            permissions_selectionnees = (
                permissions.filter(
                    id__in=permission_ids
                )
            )

            nouveau_employe.permissions_metier.set(
                permissions_selectionnees
            )

        messages.success(
            request,
            "L'employé a été créé avec succès."
        )

        return redirect(
            'employee_list'
        )

    return render(
        request,
        'accounts/employee_form.html',
        {
            'agences': agences,
            'roles': roles,
            'permissions': permissions,
            'employe': employe_connecte,
            'global_access': global_access,
        }
    )


# =========================================================
# EMPLOYES - MODIFICATION
# =========================================================


@login_required
@permission_required_metier('employees.manage')
def employee_update(
    request,
    employee_id
):

    employe_connecte = getattr(
        request.user,
        'employe',
        None
    )

    global_access = (
        has_global_agency_access(
            request.user
        )
    )

    agence_connectee = get_user_agence(
        request.user
    )

    # =====================================================
    # EMPLOYE ACCESSIBLE
    # =====================================================

    employee = get_object_or_404(
        get_accessible_employees(
            request.user
        )
        .select_related(
            'user',
            'role',
            'agence'
        )
        .prefetch_related(
            'permissions_metier'
        ),
        id=employee_id
    )

    # =====================================================
    # PROTECTION DES ROLES GLOBAUX
    # =====================================================

    if (
        not global_access
        and employee.role
        and employee.role.nom in GLOBAL_ROLE_NAMES
    ):

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à modifier "
                "un Administrateur ou un Directeur."
            )
        )

        return redirect(
            'employee_list'
        )

    # =====================================================
    # AGENCES ACCESSIBLES
    # =====================================================

    if global_access:

        agences = Agence.objects.filter(
            est_active=True
        ).order_by(
            'nom'
        )

    elif agence_connectee:

        agences = Agence.objects.filter(
            id=agence_connectee.id,
            est_active=True
        )

    else:

        agences = Agence.objects.none()

    # =====================================================
    # ROLES / PERMISSIONS AUTORISES
    # =====================================================

    roles = get_assignable_roles(
        request.user
    )

    permissions = get_assignable_permissions(
        request.user
    )

    if request.method == 'POST':

        user = employee.user

        username = (
            request.POST.get(
                'username'
            )
            or ''
        ).strip()

        first_name = (
            request.POST.get(
                'first_name'
            )
            or ''
        ).strip()

        last_name = (
            request.POST.get(
                'last_name'
            )
            or ''
        ).strip()

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip()

        new_password = (
            request.POST.get(
                'password'
            )
            or ''
        )

        role_id = (
            request.POST.get(
                'role'
            )
            or None
        )

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip() or None

        poste = (
            request.POST.get(
                'poste'
            )
            or ''
        ).strip() or None

        date_embauche = (
            request.POST.get(
                'date_embauche'
            )
            or None
        )

        est_actif = (
            request.POST.get(
                'est_actif'
            )
            == 'on'
        )

        permission_ids = (
            request.POST.getlist(
                'permissions_metier'
            )
        )

        # =================================================
        # USERNAME
        # =================================================

        if not username:

            messages.error(
                request,
                "Le nom d'utilisateur est obligatoire."
            )

            return render(
                request,
                'accounts/employee_form.html',
                {
                    'employee': employee,
                    'agences': agences,
                    'roles': roles,
                    'permissions': permissions,
                    'employe': employe_connecte,
                    'global_access': global_access,
                }
            )

        if User.objects.filter(
            username=username
        ).exclude(
            id=user.id
        ).exists():

            messages.error(
                request,
                "Ce nom d'utilisateur existe déjà."
            )

            return render(
                request,
                'accounts/employee_form.html',
                {
                    'employee': employee,
                    'agences': agences,
                    'roles': roles,
                    'permissions': permissions,
                    'employe': employe_connecte,
                    'global_access': global_access,
                }
            )

        # =================================================
        # AGENCE
        # =================================================

        if global_access:

            agence_id = (
                request.POST.get(
                    'agence'
                )
                or None
            )

            nouvelle_agence = None

            if agence_id:

                nouvelle_agence = (
                    get_object_or_404(
                        agences,
                        id=agence_id
                    )
                )

        else:

            nouvelle_agence = (
                agence_connectee
            )

        # =================================================
        # ROLE
        # =================================================

        nouveau_role = None

        if role_id:

            nouveau_role = get_object_or_404(
                roles,
                id=role_id
            )

        # =================================================
        # USER UPDATE
        # =================================================

        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        if new_password:

            user.set_password(
                new_password
            )

        user.save()

        # =================================================
        # EMPLOYE UPDATE
        # =================================================

        employee.agence = nouvelle_agence
        employee.role = nouveau_role
        employee.telephone = telephone
        employee.poste = poste
        employee.date_embauche = date_embauche
        employee.est_actif = est_actif

        employee.save()

        # =================================================
        # PERMISSIONS
        # =================================================

        if global_access:

            employee.permissions_metier.set(
                permission_ids
            )

        else:

            allowed_ids = set(
                permissions.values_list(
                    'id',
                    flat=True
                )
            )

            selected_allowed_ids = set()

            for permission_id in permission_ids:

                if not str(
                    permission_id
                ).isdigit():

                    continue

                permission_id_int = int(
                    permission_id
                )

                if permission_id_int in allowed_ids:

                    selected_allowed_ids.add(
                        permission_id_int
                    )

            existing_forbidden_ids = set(
                employee.permissions_metier
                .exclude(
                    id__in=allowed_ids
                )
                .values_list(
                    'id',
                    flat=True
                )
            )

            final_permission_ids = (
                selected_allowed_ids
                | existing_forbidden_ids
            )

            employee.permissions_metier.set(
                final_permission_ids
            )

        messages.success(
            request,
            "L'employé a été modifié avec succès."
        )

        return redirect(
            'employee_list'
        )

    return render(
        request,
        'accounts/employee_form.html',
        {
            'employee': employee,
            'agences': agences,
            'roles': roles,
            'permissions': permissions,
            'employe': employe_connecte,
            'global_access': global_access,
        }
    )


# =========================================================
# ACTIVER / DESACTIVER EMPLOYE
# =========================================================


@login_required
@permission_required_metier('employees.manage')
@require_POST
def employee_toggle_active(
    request,
    employee_id
):

    employee = get_object_or_404(
        get_accessible_employees(
            request.user
        ).select_related(
            'role'
        ),
        id=employee_id
    )

    employe_connecte = getattr(
        request.user,
        'employe',
        None
    )

    global_access = (
        has_global_agency_access(
            request.user
        )
    )

    # =====================================================
    # PROTECTION PROPRE COMPTE
    # =====================================================

    if (
        employe_connecte
        and employee.id
        == employe_connecte.id
    ):

        messages.error(
            request,
            (
                "Vous ne pouvez pas désactiver "
                "votre propre compte."
            )
        )

        return redirect(
            'employee_list'
        )

    # =====================================================
    # PROTECTION ROLE GLOBAL
    # =====================================================

    if (
        not global_access
        and employee.role
        and employee.role.nom in GLOBAL_ROLE_NAMES
    ):

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à modifier "
                "l'état d'un Administrateur ou d'un Directeur."
            )
        )

        return redirect(
            'employee_list'
        )

    # =====================================================
    # TOGGLE
    # =====================================================

    employee.est_actif = (
        not employee.est_actif
    )

    employee.save(
        update_fields=[
            'est_actif'
        ]
    )

    if employee.est_actif:

        messages.success(
            request,
            "L'employé a été activé."
        )

    else:

        messages.warning(
            request,
            "L'employé a été désactivé."
        )

    return redirect(
        'employee_list'
    )