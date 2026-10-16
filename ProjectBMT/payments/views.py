from decimal import Decimal, InvalidOperation

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib.auth.decorators import login_required
from django.contrib import messages

from accounts.decorators import (
    permission_required_metier
)

from accounts.access import (
    has_global_agency_access,
    get_user_agence
)

from notifications.models import HistoriqueAction

from .models import Paiement
from dossiers.models import Dossier


# =========================================================
# CONSTANTES
# =========================================================


TYPES_PAIEMENT_AUTORISES = [
    'AVANCE',
    'PAIEMENT',
    'SOLDE',
    'REMBOURSEMENT',
]


MODES_PAIEMENT_AUTORISES = [
    'ESPECES',
    'CARTE',
    'VIREMENT',
    'CHEQUE',
    'AUTRE',
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


def get_accessible_paiements(user):

    paiements = Paiement.objects.all()

    if has_global_agency_access(user):
        return paiements

    agence = get_user_agence(user)

    if not agence:
        return paiements.none()

    return paiements.filter(
        dossier__agence=agence
    )


# =========================================================
# HELPER - CALCUL FINANCIER SANS UN PAIEMENT
# =========================================================


def calculer_montant_paye_sans_paiement(
    dossier,
    paiement_id=None
):

    paiements = dossier.paiements.all()

    if paiement_id:

        paiements = paiements.exclude(
            id=paiement_id
        )

    total_positif = Decimal(
        '0.00'
    )

    total_remboursements = Decimal(
        '0.00'
    )

    for paiement in paiements:

        if (
            paiement.type_paiement
            == 'REMBOURSEMENT'
        ):

            total_remboursements += (
                paiement.montant
            )

        else:

            total_positif += (
                paiement.montant
            )

    montant_net = (
        total_positif
        - total_remboursements
    )

    if montant_net < 0:

        return Decimal(
            '0.00'
        )

    return montant_net


# =========================================================
# HELPER - RENDER FORM
# =========================================================


def render_paiement_form(
    request,
    dossiers,
    employe,
    paiement=None
):

    context = {
        'dossiers': dossiers,
        'employe': employe,
        'global_access': (
            has_global_agency_access(
                request.user
            )
        ),
    }

    if paiement:

        context[
            'paiement'
        ] = paiement

    return render(
        request,
        'payments/paiement_form.html',
        context
    )


# =========================================================
# LISTE DES PAIEMENTS
# =========================================================


@login_required
@permission_required_metier('payments.view')
def paiement_list(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    paiements = (
        get_accessible_paiements(
            request.user
        )
        .select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'enregistre_par',
            'enregistre_par__user'
        )
        .order_by(
            '-date_paiement'
        )
    )

    return render(
        request,
        'payments/paiement_list.html',
        {
            'paiements': paiements,
            'employe': employe,

            'global_access': (
                has_global_agency_access(
                    request.user
                )
            ),
        }
    )


# =========================================================
# CREATION PAIEMENT
# =========================================================


@login_required
@permission_required_metier('payments.manage')
def paiement_create(request):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    dossiers = (
        get_accessible_dossiers(
            request.user
        )
        .select_related(
            'client',
            'agence'
        )
        .order_by(
            '-date_creation'
        )
    )

    if request.method == 'POST':

        dossier_id = (
            request.POST.get(
                'dossier'
            )
            or None
        )

        type_paiement = (
            request.POST.get(
                'type_paiement'
            )
            or ''
        )

        montant_raw = (
            request.POST.get(
                'montant'
            )
            or '0'
        )

        mode_paiement = (
            request.POST.get(
                'mode_paiement'
            )
            or ''
        )

        reference = (
            request.POST.get(
                'reference'
            )
            or ''
        ).strip() or None

        commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # TYPE
        # =================================================

        if (
            type_paiement
            not in TYPES_PAIEMENT_AUTORISES
        ):

            messages.error(
                request,
                "Le type de paiement est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe
            )

        # =================================================
        # MODE
        # =================================================

        if (
            mode_paiement
            not in MODES_PAIEMENT_AUTORISES
        ):

            messages.error(
                request,
                "Le mode de paiement est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe
            )

        # =================================================
        # MONTANT
        # =================================================

        try:

            montant = Decimal(
                montant_raw
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le montant saisi est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe
            )

        if montant <= 0:

            messages.error(
                request,
                (
                    "Le montant doit être "
                    "supérieur à 0 MAD."
                )
            )

            return render_paiement_form(
                request,
                dossiers,
                employe
            )

        # =================================================
        # PAIEMENT POSITIF
        # =================================================

        if (
            type_paiement
            != 'REMBOURSEMENT'
        ):

            if dossier.montant_total <= 0:

                messages.error(
                    request,
                    (
                        "Le montant total du dossier "
                        "doit être défini avant "
                        "d'enregistrer un paiement."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe
                )

            reste = (
                dossier.reste_a_payer
            )

            if reste <= 0:

                messages.error(
                    request,
                    (
                        "Ce dossier est déjà "
                        "entièrement payé."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe
                )

            # =============================================
            # SOLDE
            # =============================================

            if type_paiement == 'SOLDE':

                if montant != reste:

                    messages.error(
                        request,
                        (
                            "Un paiement de type « Solde » "
                            "doit correspondre exactement "
                            "au reste à payer. "
                            f"Solde attendu : {reste} MAD."
                        )
                    )

                    return render_paiement_form(
                        request,
                        dossiers,
                        employe
                    )

            # =============================================
            # AVANCE / PAIEMENT
            # =============================================

            elif montant > reste:

                messages.error(
                    request,
                    (
                        "Le montant dépasse le reste "
                        "à payer. "
                        f"Reste actuel : {reste} MAD."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe
                )

        # =================================================
        # REMBOURSEMENT
        # =================================================

        else:

            montant_paye = (
                dossier.montant_paye
            )

            if montant_paye <= 0:

                messages.error(
                    request,
                    (
                        "Aucun montant n'a encore été payé "
                        "pour ce dossier. "
                        "Un remboursement est impossible."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe
                )

            if montant > montant_paye:

                messages.error(
                    request,
                    (
                        "Le remboursement ne peut pas "
                        "dépasser le montant net payé. "
                        f"Maximum : {montant_paye} MAD."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe
                )

        # =================================================
        # CREATION
        # =================================================

        paiement = Paiement.objects.create(

            dossier=dossier,

            enregistre_par=employe,

            type_paiement=type_paiement,

            montant=montant,

            mode_paiement=mode_paiement,

            reference=reference,

            commentaire=commentaire,
        )

        # =================================================
        # HISTORIQUE
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Création d'un paiement",

            module="Paiements",

            objet_id=paiement.id,

            description=(
                f"Paiement enregistré : "
                f"{paiement.montant} MAD - "
                f"{paiement.type_paiement} - "
                f"Dossier "
                f"{paiement.dossier.numero_dossier} - "
                f"Agence : "
                f"{paiement.dossier.agence}"
            )
        )

        messages.success(
            request,
            "Le paiement a été enregistré avec succès."
        )

        return redirect(
            'paiement_detail',
            paiement_id=paiement.id
        )

    return render_paiement_form(
        request,
        dossiers,
        employe
    )


# =========================================================
# DETAIL PAIEMENT
# =========================================================


@login_required
@permission_required_metier('payments.view')
def paiement_detail(
    request,
    paiement_id
):

    paiement = get_object_or_404(

        get_accessible_paiements(
            request.user
        )
        .select_related(
            'dossier',
            'dossier__client',
            'dossier__agence',
            'enregistre_par',
            'enregistre_par__user'
        ),

        id=paiement_id
    )

    return render(
        request,
        'payments/paiement_detail.html',
        {
            'paiement': paiement,

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
# MODIFICATION PAIEMENT
# =========================================================


@login_required
@permission_required_metier('payments.manage')
def paiement_update(
    request,
    paiement_id
):

    employe = getattr(
        request.user,
        'employe',
        None
    )

    paiement = get_object_or_404(

        get_accessible_paiements(
            request.user
        )
        .select_related(
            'dossier',
            'dossier__client',
            'dossier__agence'
        ),

        id=paiement_id
    )

    dossiers = (
        get_accessible_dossiers(
            request.user
        )
        .select_related(
            'client',
            'agence'
        )
        .order_by(
            '-date_creation'
        )
    )

    if request.method == 'POST':

        ancien_montant = (
            paiement.montant
        )

        ancien_type = (
            paiement.type_paiement
        )

        ancien_mode = (
            paiement.mode_paiement
        )

        ancien_dossier = (
            paiement.dossier
        )

        dossier_id = (
            request.POST.get(
                'dossier'
            )
            or None
        )

        type_paiement = (
            request.POST.get(
                'type_paiement'
            )
            or ''
        )

        montant_raw = (
            request.POST.get(
                'montant'
            )
            or '0'
        )

        mode_paiement = (
            request.POST.get(
                'mode_paiement'
            )
            or ''
        )

        reference = (
            request.POST.get(
                'reference'
            )
            or ''
        ).strip() or None

        commentaire = (
            request.POST.get(
                'commentaire'
            )
            or ''
        ).strip() or None

        # =================================================
        # DOSSIER
        # =================================================

        if not dossier_id:

            messages.error(
                request,
                "Veuillez sélectionner un dossier."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe,
                paiement
            )

        dossier = get_object_or_404(
            dossiers,
            id=dossier_id
        )

        # =================================================
        # TYPE
        # =================================================

        if (
            type_paiement
            not in TYPES_PAIEMENT_AUTORISES
        ):

            messages.error(
                request,
                "Le type de paiement est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe,
                paiement
            )

        # =================================================
        # MODE
        # =================================================

        if (
            mode_paiement
            not in MODES_PAIEMENT_AUTORISES
        ):

            messages.error(
                request,
                "Le mode de paiement est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe,
                paiement
            )

        # =================================================
        # MONTANT
        # =================================================

        try:

            montant = Decimal(
                montant_raw
            )

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            messages.error(
                request,
                "Le montant saisi est invalide."
            )

            return render_paiement_form(
                request,
                dossiers,
                employe,
                paiement
            )

        if montant <= 0:

            messages.error(
                request,
                (
                    "Le montant doit être "
                    "supérieur à 0 MAD."
                )
            )

            return render_paiement_form(
                request,
                dossiers,
                employe,
                paiement
            )

        # =================================================
        # CALCUL SANS LE PAIEMENT ACTUEL
        # =================================================

        paiement_a_exclure = None

        # On exclut le paiement actuel seulement
        # s'il appartient déjà au dossier sélectionné.
        #
        # S'il est déplacé vers un autre dossier,
        # il n'existe pas encore dans ce nouveau dossier.

        if (
            paiement.dossier_id
            == dossier.id
        ):

            paiement_a_exclure = (
                paiement.id
            )

        montant_paye_sans_actuel = (
            calculer_montant_paye_sans_paiement(
                dossier,
                paiement_a_exclure
            )
        )

        reste_sans_actuel = (
            dossier.montant_total
            - montant_paye_sans_actuel
        )

        if reste_sans_actuel < 0:

            reste_sans_actuel = (
                Decimal('0.00')
            )

        # =================================================
        # PAIEMENT POSITIF
        # =================================================

        if (
            type_paiement
            != 'REMBOURSEMENT'
        ):

            if dossier.montant_total <= 0:

                messages.error(
                    request,
                    (
                        "Le montant total du dossier "
                        "doit être défini avant "
                        "d'enregistrer un paiement."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe,
                    paiement
                )

            if reste_sans_actuel <= 0:

                messages.error(
                    request,
                    (
                        "Ce dossier est déjà "
                        "entièrement payé."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe,
                    paiement
                )

            # =============================================
            # SOLDE
            # =============================================

            if type_paiement == 'SOLDE':

                if montant != reste_sans_actuel:

                    messages.error(
                        request,
                        (
                            "Un paiement de type « Solde » "
                            "doit correspondre exactement "
                            "au reste à payer. "
                            f"Solde attendu : "
                            f"{reste_sans_actuel} MAD."
                        )
                    )

                    return render_paiement_form(
                        request,
                        dossiers,
                        employe,
                        paiement
                    )

            # =============================================
            # AVANCE / PAIEMENT
            # =============================================

            elif montant > reste_sans_actuel:

                messages.error(
                    request,
                    (
                        "Le montant dépasse le reste "
                        "à payer disponible. "
                        f"Maximum : "
                        f"{reste_sans_actuel} MAD."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe,
                    paiement
                )

        # =================================================
        # REMBOURSEMENT
        # =================================================

        else:

            if montant_paye_sans_actuel <= 0:

                messages.error(
                    request,
                    (
                        "Aucun montant disponible "
                        "pour effectuer ce remboursement."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe,
                    paiement
                )

            if (
                montant
                > montant_paye_sans_actuel
            ):

                messages.error(
                    request,
                    (
                        "Le remboursement dépasse "
                        "le montant net payé disponible. "
                        f"Maximum : "
                        f"{montant_paye_sans_actuel} MAD."
                    )
                )

                return render_paiement_form(
                    request,
                    dossiers,
                    employe,
                    paiement
                )

        # =================================================
        # UPDATE
        # =================================================

        paiement.dossier = (
            dossier
        )

        paiement.type_paiement = (
            type_paiement
        )

        paiement.montant = (
            montant
        )

        paiement.mode_paiement = (
            mode_paiement
        )

        paiement.reference = (
            reference
        )

        paiement.commentaire = (
            commentaire
        )

        paiement.save()

        # =================================================
        # HISTORIQUE GENERAL
        # =================================================

        HistoriqueAction.objects.create(

            employe=employe,

            action="Modification d'un paiement",

            module="Paiements",

            objet_id=paiement.id,

            description=(
                f"Paiement modifié : "
                f"{paiement.montant} MAD - "
                f"Dossier "
                f"{paiement.dossier.numero_dossier}"
            )
        )

        # =================================================
        # MONTANT
        # =================================================

        if (
            ancien_montant
            != paiement.montant
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification du montant",

                module="Paiements",

                objet_id=paiement.id,

                description=(
                    f"Dossier "
                    f"{paiement.dossier.numero_dossier} : "
                    f"{ancien_montant} MAD → "
                    f"{paiement.montant} MAD"
                )
            )

        # =================================================
        # TYPE
        # =================================================

        if (
            ancien_type
            != paiement.type_paiement
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification du type de paiement",

                module="Paiements",

                objet_id=paiement.id,

                description=(
                    f"{ancien_type} → "
                    f"{paiement.type_paiement}"
                )
            )

        # =================================================
        # MODE
        # =================================================

        if (
            ancien_mode
            != paiement.mode_paiement
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Modification du mode de paiement",

                module="Paiements",

                objet_id=paiement.id,

                description=(
                    f"{ancien_mode} → "
                    f"{paiement.mode_paiement}"
                )
            )

        # =================================================
        # DOSSIER
        # =================================================

        if (
            ancien_dossier.id
            != paiement.dossier.id
        ):

            HistoriqueAction.objects.create(

                employe=employe,

                action="Changement du dossier du paiement",

                module="Paiements",

                objet_id=paiement.id,

                description=(
                    f"{ancien_dossier.numero_dossier} → "
                    f"{paiement.dossier.numero_dossier}"
                )
            )

        messages.success(
            request,
            "Le paiement a été modifié avec succès."
        )

        return redirect(
            'paiement_detail',
            paiement_id=paiement.id
        )

    return render_paiement_form(
        request,
        dossiers,
        employe,
        paiement
    )