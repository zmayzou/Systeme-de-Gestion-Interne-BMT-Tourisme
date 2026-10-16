from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST

from accounts.decorators import (
    permission_required_metier
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from notifications.models import HistoriqueAction
from agencies.models import Agence

from .models import Client


# =========================================================
# CONSTANTES
# =========================================================


CLIENT_TYPES_AUTORISES = [
    'NOUVEAU',
    'FIDELE',
]


# =========================================================
# HELPERS - AGENCY SCOPING
# =========================================================


def get_accessible_clients(user):

    clients = Client.objects.all()

    if has_global_agency_access(user):

        return clients

    agence = get_user_agence(user)

    if not agence:

        return clients.none()

    return clients.filter(
        agence=agence
    )


def get_accessible_agences(user):

    agences = Agence.objects.filter(
        est_active=True
    )

    if has_global_agency_access(user):

        return agences

    agence = get_user_agence(user)

    if not agence:

        return agences.none()

    return agences.filter(
        id=agence.id
    )


# =========================================================
# HELPER - RENDER FORM
# =========================================================


def render_client_form(
    request,
    employe,
    agences,
    global_access,
    client=None
):

    context = {
        'employe': employe,
        'agences': agences,
        'global_access': global_access,
    }

    if client:

        context[
            'client'
        ] = client

        context[
            'client_has_dossiers'
        ] = client.dossiers.exists()

    else:

        context[
            'client_has_dossiers'
        ] = False

    return render(
        request,
        'clients/client_form.html',
        context
    )


# =========================================================
# LISTE DES CLIENTS
# =========================================================


@login_required
@permission_required_metier('clients.view')
def client_list(request):

    query = (
        request.GET.get(
            'q',
            ''
        )
        or ''
    ).strip()

    clients = (
        get_accessible_clients(
            request.user
        )
        .select_related(
            'agence',
            'cree_par',
            'cree_par__user'
        )
        .order_by(
            '-date_creation'
        )
    )

    if query:

        clients = clients.filter(

            Q(
                nom__icontains=query
            )

            |

            Q(
                prenom__icontains=query
            )

            |

            Q(
                cin__icontains=query
            )

            |

            Q(
                passeport__icontains=query
            )

            |

            Q(
                telephone__icontains=query
            )

            |

            Q(
                email__icontains=query
            )
        )

    return render(
        request,
        'clients/client_list.html',
        {
            'clients': clients,
            'query': query,

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
# CREATION CLIENT
# =========================================================


@login_required
@permission_required_metier('clients.create')
def client_create(request):

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

    agences = (
        get_accessible_agences(
            request.user
        )
        .order_by(
            'nom',
            'ville'
        )
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
                "Impossible de créer un client."
            )
        )

        return redirect(
            'client_list'
        )

    if request.method == 'POST':

        # =================================================
        # DONNEES
        # =================================================

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        prenom = (
            request.POST.get(
                'prenom'
            )
            or ''
        ).strip()

        cin = (
            request.POST.get(
                'cin'
            )
            or ''
        ).strip() or None

        passeport = (
            request.POST.get(
                'passeport'
            )
            or ''
        ).strip() or None

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip()

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip() or None

        adresse = (
            request.POST.get(
                'adresse'
            )
            or ''
        ).strip() or None

        type_client = (
            request.POST.get(
                'type_client'
            )
            or 'NOUVEAU'
        )

        autorise_sans_avance = (
            request.POST.get(
                'autorise_sans_avance'
            )
            == 'on'
        )

        # =================================================
        # NOM
        # =================================================

        if not nom:

            messages.error(
                request,
                "Le nom du client est obligatoire."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
            )

        # =================================================
        # PRENOM
        # =================================================

        if not prenom:

            messages.error(
                request,
                "Le prénom du client est obligatoire."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
            )

        # =================================================
        # TELEPHONE
        # =================================================

        if not telephone:

            messages.error(
                request,
                "Le téléphone du client est obligatoire."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
            )

        # =================================================
        # TYPE CLIENT
        # =================================================

        if (
            type_client
            not in CLIENT_TYPES_AUTORISES
        ):

            messages.error(
                request,
                "Le type du client est invalide."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
            )

        # =================================================
        # CIN UNIQUE
        # =================================================

        if (
            cin
            and Client.objects.filter(
                cin=cin
            ).exists()
        ):

            messages.error(
                request,
                (
                    "Un client avec ce CIN "
                    "existe déjà."
                )
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
            )

        # =================================================
        # PASSEPORT UNIQUE
        # =================================================

        if (
            passeport
            and Client.objects.filter(
                passeport=passeport
            ).exists()
        ):

            messages.error(
                request,
                (
                    "Un client avec ce numéro "
                    "de passeport existe déjà."
                )
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access
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

                return render_client_form(
                    request,
                    employe,
                    agences,
                    global_access
                )

            agence_client = get_object_or_404(
                agences,
                id=agence_id
            )

        else:

            # On ignore complètement toute agence
            # envoyée manuellement dans le POST.
            #
            # L'employé local crée obligatoirement
            # le client dans sa propre agence.

            agence_client = (
                user_agence
            )

        # =================================================
        # CREATION
        # =================================================

        client = Client.objects.create(

            agence=agence_client,

            cree_par=employe,

            nom=nom,

            prenom=prenom,

            cin=cin,

            passeport=passeport,

            telephone=telephone,

            email=email,

            adresse=adresse,

            type_client=type_client,

            autorise_sans_avance=(
                autorise_sans_avance
            ),
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Création d'un client",

            module="Clients",

            objet_id=client.id,

            description=(
                f"Client créé : "
                f"{client.nom} "
                f"{client.prenom} - "
                f"Agence : "
                f"{client.agence}"
            )
        )

        messages.success(
            request,
            "Le client a été créé avec succès."
        )

        return redirect(
            'client_list'
        )

    return render_client_form(
        request,
        employe,
        agences,
        global_access
    )


# =========================================================
# MODIFICATION CLIENT
# =========================================================


@login_required
@permission_required_metier('clients.update')
def client_update(
    request,
    client_id
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

    client = get_object_or_404(

        get_accessible_clients(
            request.user
        )
        .select_related(
            'agence',
            'cree_par',
            'cree_par__user'
        ),

        id=client_id
    )

    agences = (
        get_accessible_agences(
            request.user
        )
        .order_by(
            'nom',
            'ville'
        )
    )

    client_has_dossiers = (
        client.dossiers.exists()
    )

    if request.method == 'POST':

        # =================================================
        # ANCIENNES VALEURS
        # =================================================

        ancienne_agence_id = (
            client.agence_id
        )

        ancien_type = (
            client.type_client
        )

        ancienne_autorisation = (
            client.autorise_sans_avance
        )

        # =================================================
        # DONNEES
        # =================================================

        nom = (
            request.POST.get(
                'nom'
            )
            or ''
        ).strip()

        prenom = (
            request.POST.get(
                'prenom'
            )
            or ''
        ).strip()

        cin = (
            request.POST.get(
                'cin'
            )
            or ''
        ).strip() or None

        passeport = (
            request.POST.get(
                'passeport'
            )
            or ''
        ).strip() or None

        telephone = (
            request.POST.get(
                'telephone'
            )
            or ''
        ).strip()

        email = (
            request.POST.get(
                'email'
            )
            or ''
        ).strip() or None

        adresse = (
            request.POST.get(
                'adresse'
            )
            or ''
        ).strip() or None

        type_client = (
            request.POST.get(
                'type_client'
            )
            or 'NOUVEAU'
        )

        autorise_sans_avance = (
            request.POST.get(
                'autorise_sans_avance'
            )
            == 'on'
        )

        # =================================================
        # NOM / PRENOM
        # =================================================

        if not nom or not prenom:

            messages.error(
                request,
                (
                    "Le nom et le prénom "
                    "sont obligatoires."
                )
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access,
                client
            )

        # =================================================
        # TELEPHONE
        # =================================================

        if not telephone:

            messages.error(
                request,
                "Le téléphone est obligatoire."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access,
                client
            )

        # =================================================
        # TYPE
        # =================================================

        if (
            type_client
            not in CLIENT_TYPES_AUTORISES
        ):

            messages.error(
                request,
                "Le type du client est invalide."
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access,
                client
            )

        # =================================================
        # CIN
        # =================================================

        if (
            cin
            and Client.objects.filter(
                cin=cin
            ).exclude(
                id=client.id
            ).exists()
        ):

            messages.error(
                request,
                (
                    "Un autre client possède "
                    "déjà ce CIN."
                )
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access,
                client
            )

        # =================================================
        # PASSEPORT
        # =================================================

        if (
            passeport
            and Client.objects.filter(
                passeport=passeport
            ).exclude(
                id=client.id
            ).exists()
        ):

            messages.error(
                request,
                (
                    "Un autre client possède déjà "
                    "ce numéro de passeport."
                )
            )

            return render_client_form(
                request,
                employe,
                agences,
                global_access,
                client
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

                return render_client_form(
                    request,
                    employe,
                    agences,
                    global_access,
                    client
                )

            nouvelle_agence = (
                get_object_or_404(
                    agences,
                    id=agence_id
                )
            )

            # =============================================
            # PROTECTION CONSISTANCE CLIENT / DOSSIERS
            # =============================================
            #
            # Si le client possède déjà un dossier,
            # son agence ne peut plus être changée.
            #
            # Sinon :
            # Client Casablanca + Dossier Casablanca
            # pourrait devenir :
            # Client Marrakech + Dossier Casablanca.
            # =============================================

            if (
                client_has_dossiers
                and nouvelle_agence.id
                != client.agence_id
            ):

                messages.error(
                    request,
                    (
                        "Impossible de changer l'agence "
                        "de ce client car il possède déjà "
                        "un ou plusieurs dossiers."
                    )
                )

                return render_client_form(
                    request,
                    employe,
                    agences,
                    global_access,
                    client
                )

        else:

            if not user_agence:

                messages.error(
                    request,
                    (
                        "Votre compte n'est associé "
                        "à aucune agence."
                    )
                )

                return redirect(
                    'client_list'
                )

            # Employé local :
            # impossible de modifier l'agence,
            # même avec un POST falsifié.

            nouvelle_agence = (
                user_agence
            )

        # =================================================
        # UPDATE
        # =================================================

        client.agence = (
            nouvelle_agence
        )

        client.nom = (
            nom
        )

        client.prenom = (
            prenom
        )

        client.cin = (
            cin
        )

        client.passeport = (
            passeport
        )

        client.telephone = (
            telephone
        )

        client.email = (
            email
        )

        client.adresse = (
            adresse
        )

        client.type_client = (
            type_client
        )

        client.autorise_sans_avance = (
            autorise_sans_avance
        )

        client.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Modification d'un client",

            module="Clients",

            objet_id=client.id,

            description=(
                f"Client modifié : "
                f"{client.nom} "
                f"{client.prenom}"
            )
        )

        # =================================================
        # CHANGEMENT AGENCE
        # =================================================

        if (
            ancienne_agence_id
            != client.agence_id
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement d'agence client",

                module="Clients",

                objet_id=client.id,

                description=(
                    f"Nouvelle agence : "
                    f"{client.agence}"
                )
            )

        # =================================================
        # TYPE CLIENT
        # =================================================

        if (
            ancien_type
            != client.type_client
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement du type client",

                module="Clients",

                objet_id=client.id,

                description=(
                    f"{ancien_type} → "
                    f"{client.type_client}"
                )
            )

        # =================================================
        # AUTORISATION SANS AVANCE
        # =================================================

        if (
            ancienne_autorisation
            != client.autorise_sans_avance
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification autorisation avance",

                module="Clients",

                objet_id=client.id,

                description=(
                    "Autorisation sans avance : "
                    f"{'Oui' if client.autorise_sans_avance else 'Non'}"
                )
            )

        messages.success(
            request,
            "Le client a été modifié avec succès."
        )

        return redirect(
            'client_list'
        )

    return render_client_form(
        request,
        employe,
        agences,
        global_access,
        client
    )


# =========================================================
# SUPPRESSION CLIENT
# =========================================================


@login_required
@permission_required_metier('clients.delete')
@require_POST
def client_delete(
    request,
    client_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    client = get_object_or_404(

        get_accessible_clients(
            request.user
        )
        .select_related(
            'agence'
        ),

        id=client_id
    )

    # =====================================================
    # PROTECTION DOSSIERS
    # =====================================================

    if client.dossiers.exists():

        messages.error(
            request,
            (
                "Impossible de supprimer ce client "
                "car il possède déjà "
                "un ou plusieurs dossiers."
            )
        )

        return redirect(
            'client_list'
        )

    client_name = (
        f"{client.nom} "
        f"{client.prenom}"
    )

    agence_name = (
        str(client.agence)
        if client.agence
        else "Aucune agence"
    )

    client_id_saved = (
        client.id
    )

    client.delete()

    # =====================================================
    # HISTORIQUE
    # =====================================================

    HistoriqueAction.objects.create(

        employe=employe,

        action="Suppression d'un client",

        module="Clients",

        objet_id=client_id_saved,

        description=(
            f"Client supprimé : "
            f"{client_name} - "
            f"Agence : {agence_name}"
        )
    )

    messages.success(
        request,
        "Le client a été supprimé."
    )

    return redirect(
        'client_list'
    )