from decimal import Decimal, InvalidOperation

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib import messages

from accounts.decorators import (
    permission_required_metier
)

from accounts.access import (
    get_user_agence,
    has_global_agency_access
)

from notifications.models import HistoriqueAction

from .models import (
    Dossier,
    Document
)

from clients.models import Client
from agencies.models import Agence


# =========================================================
# CONSTANTES
# =========================================================


DOSSIER_STATUTS = [
    'NOUVEAU',
    'EN_COURS',
    'EN_ATTENTE',
    'BLOQUE',
    'TERMINE',
    'ANNULE',
]


DOSSIER_TYPES_SERVICE = [
    'VISA',
    'BILLETTERIE',
    'VOYAGE',
    'HOTEL',
    'AUTRE',
]


DOCUMENT_STATUTS = [
    'RECU',
    'VALIDE',
    'MANQUANT',
    'REFUSE',
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


def get_accessible_agences(user):

    agences = Agence.objects.filter(
        est_active=True
    )

    if has_global_agency_access(user):

        return agences.order_by(
            'nom',
            'ville'
        )

    agence = get_user_agence(user)

    if not agence:

        return agences.none()

    return agences.filter(
        id=agence.id
    ).order_by(
        'nom',
        'ville'
    )


def get_accessible_clients(user):

    clients = Client.objects.select_related(
        'agence',
        'cree_par'
    )

    # Admin / Directeur / Superuser
    if has_global_agency_access(user):

        return clients.order_by(
            'nom',
            'prenom'
        )

    # Employé local
    agence = get_user_agence(user)

    if not agence:

        return clients.none()

    return clients.filter(
        agence=agence
    ).order_by(
        'nom',
        'prenom'
    )


# =========================================================
# VALIDATION CLIENT / AGENCE
# =========================================================


def client_matches_agence(client, agence):

    if not client:
        return False

    if not agence:
        return False

    if not client.agence_id:
        return False

    return (
        client.agence_id
        == agence.id
    )


# =========================================================
# DOSSIERS - LISTE
# =========================================================


@login_required
@permission_required_metier('dossiers.view')
def dossier_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    query = (
        request.GET.get(
            'q',
            ''
        )
        or ''
    ).strip()

    dossiers = (
        get_accessible_dossiers(
            request.user
        )
        .select_related(
            'client',
            'client__agence',
            'agence',
            'cree_par',
            'cree_par__user'
        )
        .order_by(
            '-date_creation'
        )
    )

    if query:

        dossiers = dossiers.filter(

            Q(
                numero_dossier__icontains=query
            )

            |

            Q(
                client__nom__icontains=query
            )

            |

            Q(
                client__prenom__icontains=query
            )

            |

            Q(
                type_service__icontains=query
            )

            |

            Q(
                statut__icontains=query
            )
        )

    return render(
        request,
        'dossiers/dossier_list.html',
        {
            'dossiers': dossiers,
            'query': query,

            'employe': employe,

            'global_access': (
                has_global_agency_access(
                    request.user
                )
            ),
        }
    )


# =========================================================
# DOSSIERS - CREATION
# =========================================================


@login_required
@permission_required_metier('dossiers.create')
def dossier_create(request):

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

    user_agence = get_user_agence(
        request.user
    )

    clients = get_accessible_clients(
        request.user
    )

    agences = get_accessible_agences(
        request.user
    )

    # =====================================================
    # EMPLOYE LOCAL SANS AGENCE
    # =====================================================

    if (
        not global_access
        and not user_agence
    ):

        messages.error(
            request,
            (
                "Votre compte n'est associé "
                "à aucune agence. "
                "Impossible de créer un dossier."
            )
        )

        return redirect(
            'dossier_list'
        )

    if request.method == 'POST':

        # =================================================
        # RECUPERATION DES DONNEES
        # =================================================

        client_id = (
            request.POST.get(
                'client'
            )
            or None
        )

        numero_dossier = (
            request.POST.get(
                'numero_dossier'
            )
            or ''
        ).strip()

        type_service = (
            request.POST.get(
                'type_service'
            )
            or ''
        )

        statut = (
            request.POST.get(
                'statut'
            )
            or 'NOUVEAU'
        )

        description = (
            request.POST.get(
                'description'
            )
            or ''
        ).strip() or None

        montant_total_raw = (
            request.POST.get(
                'montant_total'
            )
            or '0'
        )

        # =================================================
        # CLIENT
        # =================================================

        if not client_id:

            messages.error(
                request,
                "Veuillez sélectionner un client."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        client = get_object_or_404(
            clients,
            id=client_id
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

            if not agence_id:

                messages.error(
                    request,
                    "Veuillez sélectionner une agence."
                )

                return render(
                    request,
                    'dossiers/dossier_form.html',
                    {
                        'clients': clients,
                        'agences': agences,
                        'employe': employe,
                        'global_access': global_access,
                    }
                )

            agence = get_object_or_404(
                agences,
                id=agence_id
            )

        else:

            # L'agence envoyée par le navigateur
            # est complètement ignorée.
            #
            # L'employé travaille uniquement
            # avec son agence.

            agence = user_agence

        # =================================================
        # CONSISTANCE CLIENT / AGENCE
        # =================================================

        if not client.agence_id:

            messages.error(
                request,
                (
                    "Ce client n'est associé à aucune agence. "
                    "Veuillez d'abord attribuer une agence "
                    "au client."
                )
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        if not client_matches_agence(
            client,
            agence
        ):

            messages.error(
                request,
                (
                    "Le client sélectionné appartient "
                    "à une autre agence. "
                    "Le client et le dossier doivent "
                    "appartenir à la même agence."
                )
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # NUMERO DOSSIER
        # =================================================

        if not numero_dossier:

            messages.error(
                request,
                "Le numéro du dossier est obligatoire."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        if Dossier.objects.filter(
            numero_dossier=numero_dossier
        ).exists():

            messages.error(
                request,
                "Ce numéro de dossier existe déjà."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # TYPE SERVICE
        # =================================================

        if (
            type_service
            not in DOSSIER_TYPES_SERVICE
        ):

            messages.error(
                request,
                "Le type de service sélectionné est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in DOSSIER_STATUTS:

            messages.error(
                request,
                "Le statut du dossier est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # MONTANT
        # =================================================

        try:

            montant_total = Decimal(
                montant_total_raw
            )

            if montant_total < 0:

                messages.error(
                    request,
                    (
                        "Le montant total ne peut "
                        "pas être négatif."
                    )
                )

                return render(
                    request,
                    'dossiers/dossier_form.html',
                    {
                        'clients': clients,
                        'agences': agences,
                        'employe': employe,
                        'global_access': global_access,
                    }
                )

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le montant total est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # REGLE AVANCE
        # =================================================

        avance_requise = (
            not client.autorise_sans_avance
        )

        # Nouveau dossier = aucun paiement.
        #
        # Si le client doit obligatoirement
        # verser une avance, le dossier
        # ne peut pas démarrer immédiatement.

        if (
            avance_requise
            and statut == 'EN_COURS'
        ):

            statut = 'EN_ATTENTE'

            messages.warning(
                request,
                (
                    "Ce client doit verser une avance "
                    "avant le traitement du dossier. "
                    "Le dossier a été placé en attente."
                )
            )

        # =================================================
        # CREATION
        # =================================================

        dossier = Dossier.objects.create(

            client=client,

            agence=agence,

            cree_par=employe,

            numero_dossier=numero_dossier,

            type_service=type_service,

            statut=statut,

            description=description,

            montant_total=montant_total,

            avance_requise=avance_requise,
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Création d'un dossier",

            module="Dossiers",

            objet_id=dossier.id,

            description=(
                f"Dossier créé : "
                f"{dossier.numero_dossier} "
                f"pour {dossier.client} - "
                f"Agence : {dossier.agence} - "
                f"Montant : "
                f"{dossier.montant_total} MAD"
            )
        )

        messages.success(
            request,
            "Le dossier a été créé avec succès."
        )

        return redirect(
            'dossier_detail',
            dossier_id=dossier.id
        )

    return render(
        request,
        'dossiers/dossier_form.html',
        {
            'clients': clients,
            'agences': agences,
            'employe': employe,
            'global_access': global_access,
        }
    )


# =========================================================
# DOSSIER - DETAIL
# =========================================================


@login_required
@permission_required_metier('dossiers.view')
def dossier_detail(
    request,
    dossier_id
):

    dossier = get_object_or_404(

        get_accessible_dossiers(
            request.user
        )
        .select_related(
            'client',
            'client__agence',
            'agence',
            'cree_par',
            'cree_par__user'
        )
        .prefetch_related(
            'documents',
            'paiements',
            'taches'
        ),

        id=dossier_id
    )

    return render(
        request,
        'dossiers/dossier_detail.html',
        {
            'dossier': dossier,

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
# DOSSIER - MODIFICATION
# =========================================================


@login_required
@permission_required_metier('dossiers.update')
def dossier_update(
    request,
    dossier_id
):

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

    user_agence = get_user_agence(
        request.user
    )

    # =====================================================
    # DOSSIER ACCESSIBLE
    # =====================================================

    dossier = get_object_or_404(

        get_accessible_dossiers(
            request.user
        )
        .select_related(
            'client',
            'client__agence',
            'agence'
        ),

        id=dossier_id
    )

    clients = get_accessible_clients(
        request.user
    )

    agences = get_accessible_agences(
        request.user
    )

    if request.method == 'POST':

        # =================================================
        # ANCIENNES VALEURS
        # =================================================

        ancien_statut = (
            dossier.statut
        )

        ancien_montant = (
            dossier.montant_total
        )

        ancienne_avance_requise = (
            dossier.avance_requise
        )

        ancienne_agence_id = (
            dossier.agence_id
        )

        ancien_client_id = (
            dossier.client_id
        )

        ancien_type_service = (
            dossier.type_service
        )

        # =================================================
        # CLIENT
        # =================================================

        client_id = (
            request.POST.get(
                'client'
            )
            or None
        )

        if not client_id:

            messages.error(
                request,
                "Veuillez sélectionner un client."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        client = get_object_or_404(
            clients,
            id=client_id
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

            if not agence_id:

                messages.error(
                    request,
                    "Veuillez sélectionner une agence."
                )

                return render(
                    request,
                    'dossiers/dossier_form.html',
                    {
                        'dossier': dossier,
                        'clients': clients,
                        'agences': agences,
                        'employe': employe,
                        'global_access': global_access,
                    }
                )

            agence = get_object_or_404(
                agences,
                id=agence_id
            )

        else:

            # L'employé local ne peut jamais
            # transférer un dossier vers
            # une autre agence.

            agence = user_agence

        # =================================================
        # CONSISTANCE CLIENT / AGENCE
        # =================================================

        if not client.agence_id:

            messages.error(
                request,
                (
                    "Ce client n'est associé à aucune agence. "
                    "Veuillez d'abord attribuer une agence "
                    "au client."
                )
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        if not client_matches_agence(
            client,
            agence
        ):

            messages.error(
                request,
                (
                    "Le client sélectionné appartient "
                    "à une autre agence. "
                    "Le dossier et le client doivent "
                    "appartenir à la même agence."
                )
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # NUMERO DOSSIER
        # =================================================

        numero_dossier = (
            request.POST.get(
                'numero_dossier'
            )
            or ''
        ).strip()

        if not numero_dossier:

            messages.error(
                request,
                "Le numéro du dossier est obligatoire."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        if Dossier.objects.filter(
            numero_dossier=numero_dossier
        ).exclude(
            id=dossier.id
        ).exists():

            messages.error(
                request,
                "Ce numéro de dossier existe déjà."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # TYPE SERVICE
        # =================================================

        type_service = (
            request.POST.get(
                'type_service'
            )
            or ''
        )

        if (
            type_service
            not in DOSSIER_TYPES_SERVICE
        ):

            messages.error(
                request,
                "Le type de service sélectionné est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # STATUT
        # =================================================

        nouveau_statut = (
            request.POST.get(
                'statut'
            )
            or ''
        )

        if (
            nouveau_statut
            not in DOSSIER_STATUTS
        ):

            messages.error(
                request,
                "Le statut du dossier est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # MONTANT
        # =================================================

        montant_total_raw = (
            request.POST.get(
                'montant_total'
            )
            or '0'
        )

        try:

            montant_total = Decimal(
                montant_total_raw
            )

            if montant_total < 0:

                messages.error(
                    request,
                    (
                        "Le montant total ne peut "
                        "pas être négatif."
                    )
                )

                return render(
                    request,
                    'dossiers/dossier_form.html',
                    {
                        'dossier': dossier,
                        'clients': clients,
                        'agences': agences,
                        'employe': employe,
                        'global_access': global_access,
                    }
                )

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le montant total est invalide."
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # REGLE AVANCE
        # =================================================

        nouvelle_avance_requise = (
            not client.autorise_sans_avance
        )

        if (
            nouveau_statut == 'EN_COURS'
            and nouvelle_avance_requise
            and not dossier.avance_versee
        ):

            messages.error(
                request,
                (
                    "Impossible de passer ce dossier "
                    "au statut « En cours » : "
                    "une avance doit d'abord être "
                    "enregistrée."
                )
            )

            return render(
                request,
                'dossiers/dossier_form.html',
                {
                    'dossier': dossier,
                    'clients': clients,
                    'agences': agences,
                    'employe': employe,
                    'global_access': global_access,
                }
            )

        # =================================================
        # DESCRIPTION
        # =================================================

        description = (
            request.POST.get(
                'description'
            )
            or ''
        ).strip() or None

        # =================================================
        # UPDATE
        # =================================================

        dossier.client = client

        dossier.agence = agence

        dossier.numero_dossier = (
            numero_dossier
        )

        dossier.type_service = (
            type_service
        )

        dossier.statut = (
            nouveau_statut
        )

        dossier.description = (
            description
        )

        dossier.montant_total = (
            montant_total
        )

        dossier.avance_requise = (
            nouvelle_avance_requise
        )

        dossier.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Modification d'un dossier",

            module="Dossiers",

            objet_id=dossier.id,

            description=(
                f"Dossier modifié : "
                f"{dossier.numero_dossier}"
            )
        )

        # =================================================
        # CHANGEMENT CLIENT
        # =================================================

        if (
            ancien_client_id
            != dossier.client_id
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement de client du dossier",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} → "
                    f"{dossier.client}"
                )
            )

        # =================================================
        # CHANGEMENT STATUT
        # =================================================

        if (
            ancien_statut
            != dossier.statut
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement de statut dossier",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} : "
                    f"{ancien_statut} → "
                    f"{dossier.statut}"
                )
            )

        # =================================================
        # CHANGEMENT TYPE SERVICE
        # =================================================

        if (
            ancien_type_service
            != dossier.type_service
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement du service du dossier",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} : "
                    f"{ancien_type_service} → "
                    f"{dossier.type_service}"
                )
            )

        # =================================================
        # CHANGEMENT MONTANT
        # =================================================

        if (
            ancien_montant
            != dossier.montant_total
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification du montant du dossier",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} : "
                    f"{ancien_montant} MAD → "
                    f"{dossier.montant_total} MAD"
                )
            )

        # =================================================
        # CHANGEMENT REGLE AVANCE
        # =================================================

        if (
            ancienne_avance_requise
            != dossier.avance_requise
        ):

            if dossier.avance_requise:

                texte_avance = (
                    "Avance requise"
                )

            else:

                texte_avance = (
                    "Client autorisé sans avance"
                )

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification de la règle d'avance",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} : "
                    f"{texte_avance}"
                )
            )

        # =================================================
        # CHANGEMENT AGENCE
        # =================================================

        if (
            ancienne_agence_id
            != dossier.agence_id
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement d'agence du dossier",

                module="Dossiers",

                objet_id=dossier.id,

                description=(
                    f"{dossier.numero_dossier} → "
                    f"{dossier.agence}"
                )
            )

        messages.success(
            request,
            "Le dossier a été modifié avec succès."
        )

        return redirect(
            'dossier_detail',
            dossier_id=dossier.id
        )

    return render(
        request,
        'dossiers/dossier_form.html',
        {
            'dossier': dossier,
            'clients': clients,
            'agences': agences,
            'employe': employe,
            'global_access': global_access,
        }
    )


# =========================================================
# DOCUMENT - CREATION
# =========================================================


@login_required
@permission_required_metier('documents.manage')
def document_create(
    request,
    dossier_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    dossier = get_object_or_404(
        get_accessible_dossiers(
            request.user
        ),
        id=dossier_id
    )

    if request.method == 'POST':

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or 'RECU'
        )

        commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        # =================================================
        # VALIDATION NOM
        # =================================================

        if not nom:

            messages.error(
                request,
                "Le nom du document est obligatoire."
            )

            return render(
                request,
                'dossiers/document_form.html',
                {
                    'dossier': dossier,
                    'employe': employe,
                }
            )

        # =================================================
        # VALIDATION STATUT
        # =================================================

        if statut not in DOCUMENT_STATUTS:

            messages.error(
                request,
                "Le statut du document est invalide."
            )

            return render(
                request,
                'dossiers/document_form.html',
                {
                    'dossier': dossier,
                    'employe': employe,
                }
            )

        # =================================================
        # CREATION
        # =================================================

        document = Document.objects.create(

            dossier=dossier,

            ajoute_par=employe,

            nom=nom,

            fichier=request.FILES.get(
                'fichier'
            ),

            statut=statut,

            commentaire=commentaire,
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Ajout d'un document",

            module="Documents",

            objet_id=document.id,

            description=(
                f"Document ajouté : "
                f"{document.nom} "
                f"dans le dossier "
                f"{dossier.numero_dossier}"
            )
        )

        messages.success(
            request,
            "Le document a été ajouté avec succès."
        )

        return redirect(
            'dossier_detail',
            dossier_id=dossier.id
        )

    return render(
        request,
        'dossiers/document_form.html',
        {
            'dossier': dossier,
            'employe': employe,
        }
    )


# =========================================================
# DOCUMENT - MODIFICATION
# =========================================================


@login_required
@permission_required_metier('documents.manage')
def document_update(
    request,
    document_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    accessible_dossiers = (
        get_accessible_dossiers(
            request.user
        )
    )

    document = get_object_or_404(

        Document.objects
        .select_related(
            'dossier',
            'dossier__agence'
        )
        .filter(
            dossier__in=accessible_dossiers
        ),

        id=document_id
    )

    dossier = document.dossier

    if request.method == 'POST':

        ancien_statut = (
            document.statut
        )

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        statut = (
            request.POST.get(
                'statut'
            )
            or document.statut
        )

        commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        # =================================================
        # NOM
        # =================================================

        if not nom:

            messages.error(
                request,
                "Le nom du document est obligatoire."
            )

            return render(
                request,
                'dossiers/document_form.html',
                {
                    'document': document,
                    'dossier': dossier,
                    'employe': employe,
                }
            )

        # =================================================
        # STATUT
        # =================================================

        if statut not in DOCUMENT_STATUTS:

            messages.error(
                request,
                "Le statut du document est invalide."
            )

            return render(
                request,
                'dossiers/document_form.html',
                {
                    'document': document,
                    'dossier': dossier,
                    'employe': employe,
                }
            )

        # =================================================
        # UPDATE
        # =================================================

        document.nom = (
            nom
        )

        document.statut = (
            statut
        )

        document.commentaire = (
            commentaire
        )

        nouveau_fichier = (
            request.FILES.get(
                'fichier'
            )
        )

        if nouveau_fichier:

            document.fichier = (
                nouveau_fichier
            )

        document.save()

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Modification d'un document",

            module="Documents",

            objet_id=document.id,

            description=(
                f"Document modifié : "
                f"{document.nom} "
                f"dans le dossier "
                f"{dossier.numero_dossier}"
            )
        )

        if (
            ancien_statut
            != document.statut
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement de statut document",

                module="Documents",

                objet_id=document.id,

                description=(
                    f"{document.nom} : "
                    f"{ancien_statut} → "
                    f"{document.statut}"
                )
            )

        messages.success(
            request,
            "Le document a été modifié avec succès."
        )

        return redirect(
            'dossier_detail',
            dossier_id=dossier.id
        )

    return render(
        request,
        'dossiers/document_form.html',
        {
            'document': document,
            'dossier': dossier,
            'employe': employe,
        }
    )


# =========================================================
# DOCUMENT - SUPPRESSION
# =========================================================


@login_required
@permission_required_metier('documents.manage')
def document_delete(
    request,
    document_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    accessible_dossiers = (
        get_accessible_dossiers(
            request.user
        )
    )

    document = get_object_or_404(

        Document.objects
        .select_related(
            'dossier',
            'dossier__agence'
        )
        .filter(
            dossier__in=accessible_dossiers
        ),

        id=document_id
    )

    dossier_id = (
        document.dossier.id
    )

    dossier_numero = (
        document.dossier.numero_dossier
    )

    if request.method == 'POST':

        document_name = (
            document.nom
        )

        document_id_saved = (
            document.id
        )

        document.delete()

        HistoriqueAction.objects.create(

            employe=employe,

            action="Suppression d'un document",

            module="Documents",

            objet_id=document_id_saved,

            description=(
                f"Document supprimé : "
                f"{document_name} "
                f"du dossier "
                f"{dossier_numero}"
            )
        )

        messages.success(
            request,
            "Le document a été supprimé avec succès."
        )

        return redirect(
            'dossier_detail',
            dossier_id=dossier_id
        )

    return render(
        request,
        'dossiers/document_confirm_delete.html',
        {
            'document': document,
            'employe': employe,
        }
    )