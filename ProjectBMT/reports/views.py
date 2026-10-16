from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count

from accounts.decorators import permission_required_metier

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from clients.models import Client
from dossiers.models import Dossier
from payments.models import Paiement
from visa.models import Visa
from ticketing.models import Billet
from guides.models import MissionGuide
from agencies.models import Agence


# =========================================================
# CONSTANTES
# =========================================================

ZERO = Decimal('0.00')


# =========================================================
# REPORT DASHBOARD
# =========================================================


@login_required
@permission_required_metier('reports.view')
def report_dashboard(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    global_access = has_global_agency_access(
        request.user
    )

    agence = get_user_agence(
        request.user
    )

    # =====================================================
    # QUERYSETS ACCESSIBLES
    # =====================================================

    if global_access:

        clients = Client.objects.all()

        dossiers = Dossier.objects.all()

        paiements = Paiement.objects.all()

        visas = Visa.objects.all()

        billets = Billet.objects.all()

        missions = MissionGuide.objects.all()

        agences = Agence.objects.all()

    elif agence:

        clients = Client.objects.filter(
            agence=agence
        )

        dossiers = Dossier.objects.filter(
            agence=agence
        )

        paiements = Paiement.objects.filter(
            dossier__agence=agence
        )

        visas = Visa.objects.filter(
            dossier__agence=agence
        )

        billets = Billet.objects.filter(
            dossier__agence=agence
        )

        missions = MissionGuide.objects.filter(
            dossier__agence=agence
        )

        agences = Agence.objects.filter(
            id=agence.id
        )

    else:

        clients = Client.objects.none()

        dossiers = Dossier.objects.none()

        paiements = Paiement.objects.none()

        visas = Visa.objects.none()

        billets = Billet.objects.none()

        missions = MissionGuide.objects.none()

        agences = Agence.objects.none()

    # =====================================================
    # CLIENTS
    # =====================================================

    total_clients = clients.count()

    nouveaux_clients = clients.filter(
        type_client='NOUVEAU'
    ).count()

    clients_fideles = clients.filter(
        type_client='FIDELE'
    ).count()

    # =====================================================
    # DOSSIERS
    # =====================================================

    total_dossiers = dossiers.count()

    dossiers_nouveaux = dossiers.filter(
        statut='NOUVEAU'
    ).count()

    dossiers_en_cours = dossiers.filter(
        statut='EN_COURS'
    ).count()

    dossiers_en_attente = dossiers.filter(
        statut='EN_ATTENTE'
    ).count()

    dossiers_bloques = dossiers.filter(
        statut='BLOQUE'
    ).count()

    dossiers_termines = dossiers.filter(
        statut='TERMINE'
    ).count()

    dossiers_annules = dossiers.filter(
        statut='ANNULE'
    ).count()

    # =====================================================
    # PAIEMENTS
    # =====================================================

    total_paiements = paiements.count()

    # -----------------------------------------------------
    # TOTAL BRUT
    #
    # Attention :
    # ce montant additionne aussi les remboursements.
    # Il représente donc le volume brut des opérations
    # enregistrées et non l'encaissement réel.
    # -----------------------------------------------------

    montant_paiements_brut = (
        paiements.aggregate(
            total=Sum('montant')
        )['total']
        or ZERO
    )

    # -----------------------------------------------------
    # AVANCES
    # -----------------------------------------------------

    montant_avances = (
        paiements.filter(
            type_paiement='AVANCE'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or ZERO
    )

    # -----------------------------------------------------
    # PAIEMENTS CLASSIQUES
    # -----------------------------------------------------

    montant_paiements_classiques = (
        paiements.filter(
            type_paiement='PAIEMENT'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or ZERO
    )

    # -----------------------------------------------------
    # SOLDES
    # -----------------------------------------------------

    montant_soldes = (
        paiements.filter(
            type_paiement='SOLDE'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or ZERO
    )

    # -----------------------------------------------------
    # REMBOURSEMENTS
    # -----------------------------------------------------

    montant_remboursements = (
        paiements.filter(
            type_paiement='REMBOURSEMENT'
        ).aggregate(
            total=Sum('montant')
        )['total']
        or ZERO
    )

    # -----------------------------------------------------
    # ENCAISSEMENT NET
    #
    # Avances
    # + Paiements
    # + Soldes
    # - Remboursements
    # -----------------------------------------------------

    montant_net_paiements = (
        montant_avances
        + montant_paiements_classiques
        + montant_soldes
        - montant_remboursements
    )

    # Protection d'affichage.
    if montant_net_paiements < ZERO:
        montant_net_paiements = ZERO

    # -----------------------------------------------------
    # COMPATIBILITE ANCIEN TEMPLATE
    # -----------------------------------------------------

    montant_total_paiements = (
        montant_net_paiements
    )

    # =====================================================
    # VISA
    # =====================================================

    total_visas = visas.count()

    visas_en_traitement = visas.filter(
        statut='EN_TRAITEMENT'
    ).count()

    visas_acceptes = visas.filter(
        statut='ACCEPTE'
    ).count()

    visas_refuses = visas.filter(
        statut='REFUSE'
    ).count()

    # =====================================================
    # BILLETTERIE
    # =====================================================

    total_billets = billets.count()

    billets_reserves = billets.filter(
        statut='RESERVE'
    ).count()

    billets_emis = billets.filter(
        statut='BILLET_EMIS'
    ).count()

    billets_annules = billets.filter(
        statut='ANNULE'
    ).count()

    # -----------------------------------------------------
    # VALEUR DES BILLETS
    #
    # Ce montant représente la somme des prix des billets.
    #
    # Ce n'est PAS forcément le chiffre d'affaires
    # ni le bénéfice de l'agence.
    #
    # Pour calculer une marge réelle, il faudrait par
    # exemple ajouter :
    #
    # - coût d'achat
    # - commission
    # - frais de service
    # - marge
    # -----------------------------------------------------

    valeur_billets = (
        billets.aggregate(
            total=Sum('prix')
        )['total']
        or ZERO
    )

    # Compatibilité temporaire avec l'ancien template.
    # À supprimer lorsque le template utilisera uniquement
    # "valeur_billets".

    chiffre_billetterie = valeur_billets

    # =====================================================
    # MISSIONS
    # =====================================================

    total_missions = missions.count()

    missions_planifiees = missions.filter(
        statut='PLANIFIEE'
    ).count()

    missions_en_cours = missions.filter(
        statut='EN_COURS'
    ).count()

    missions_terminees = missions.filter(
        statut='TERMINEE'
    ).count()

    missions_annulees = missions.filter(
        statut='ANNULEE'
    ).count()

    # =====================================================
    # STATISTIQUES PAR AGENCE
    # =====================================================

    agences_stats = agences.annotate(

        nombre_dossiers=Count(
            'dossiers',
            distinct=True
        ),

        nombre_employes=Count(
            'employes',
            distinct=True
        )

    ).order_by(
        'ville'
    )

    # =====================================================
    # DOSSIERS PAR SERVICE
    # =====================================================

    dossiers_par_service = (
        dossiers
        .values(
            'type_service'
        )
        .annotate(
            total=Count(
                'id'
            )
        )
        .order_by(
            '-total'
        )
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        # -------------------------------------------------
        # UTILISATEUR
        # -------------------------------------------------

        'employe': employe,

        'global_access': global_access,

        'agence': agence,

        # -------------------------------------------------
        # CLIENTS
        # -------------------------------------------------

        'total_clients': total_clients,

        'nouveaux_clients': nouveaux_clients,

        'clients_fideles': clients_fideles,

        # -------------------------------------------------
        # DOSSIERS
        # -------------------------------------------------

        'total_dossiers': total_dossiers,

        'dossiers_nouveaux': dossiers_nouveaux,

        'dossiers_en_cours': dossiers_en_cours,

        'dossiers_en_attente': dossiers_en_attente,

        'dossiers_bloques': dossiers_bloques,

        'dossiers_termines': dossiers_termines,

        'dossiers_annules': dossiers_annules,

        # -------------------------------------------------
        # PAIEMENTS
        # -------------------------------------------------

        'total_paiements': total_paiements,

        'montant_total_paiements':
            montant_total_paiements,

        'montant_paiements_brut':
            montant_paiements_brut,

        'montant_net_paiements':
            montant_net_paiements,

        'montant_avances':
            montant_avances,

        'montant_paiements_classiques':
            montant_paiements_classiques,

        'montant_soldes':
            montant_soldes,

        'montant_remboursements':
            montant_remboursements,

        # -------------------------------------------------
        # VISA
        # -------------------------------------------------

        'total_visas':
            total_visas,

        'visas_en_traitement':
            visas_en_traitement,

        'visas_acceptes':
            visas_acceptes,

        'visas_refuses':
            visas_refuses,

        # -------------------------------------------------
        # BILLETTERIE
        # -------------------------------------------------

        'total_billets':
            total_billets,

        'billets_reserves':
            billets_reserves,

        'billets_emis':
            billets_emis,

        'billets_annules':
            billets_annules,

        'valeur_billets':
            valeur_billets,

        # Ancienne variable gardée temporairement.
        'chiffre_billetterie':
            chiffre_billetterie,

        # -------------------------------------------------
        # MISSIONS
        # -------------------------------------------------

        'total_missions':
            total_missions,

        'missions_planifiees':
            missions_planifiees,

        'missions_en_cours':
            missions_en_cours,

        'missions_terminees':
            missions_terminees,

        'missions_annulees':
            missions_annulees,

        # -------------------------------------------------
        # AGENCES
        # -------------------------------------------------

        'agences_stats':
            agences_stats,

        # -------------------------------------------------
        # SERVICES
        # -------------------------------------------------

        'dossiers_par_service':
            dossiers_par_service,
    }

    return render(
        request,
        'reports/report_dashboard.html',
        context
    )