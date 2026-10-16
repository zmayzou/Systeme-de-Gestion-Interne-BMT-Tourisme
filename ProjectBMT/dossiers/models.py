from decimal import Decimal

from django.db import models
from django.db.models import Sum

from clients.models import Client
from agencies.models import Agence
from accounts.models import Employe


class Dossier(models.Model):

    STATUT_CHOICES = [
        ('NOUVEAU', 'Nouveau'),
        ('EN_COURS', 'En cours'),
        ('EN_ATTENTE', 'En attente'),
        ('BLOQUE', 'Bloqué'),
        ('TERMINE', 'Terminé'),
        ('ANNULE', 'Annulé'),
    ]

    TYPE_SERVICE_CHOICES = [
        ('VISA', 'Visa'),
        ('BILLETTERIE', 'Billetterie'),
        ('VOYAGE', 'Voyage organisé'),
        ('HOTEL', 'Réservation hôtel'),
        ('AUTRE', 'Autre'),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='dossiers'
    )

    agence = models.ForeignKey(
        Agence,
        on_delete=models.PROTECT,
        related_name='dossiers'
    )

    cree_par = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        related_name='dossiers_crees'
    )

    numero_dossier = models.CharField(
        max_length=50,
        unique=True
    )

    type_service = models.CharField(
        max_length=30,
        choices=TYPE_SERVICE_CHOICES
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='NOUVEAU'
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # =====================================================
    # FINANCES
    # =====================================================

    montant_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    avance_requise = models.BooleanField(
        default=True
    )

    # =====================================================
    # DATES
    # =====================================================

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.numero_dossier

    # =====================================================
    # TOTAL DES PAIEMENTS POSITIFS
    # =====================================================

    @property
    def total_paiements_positifs(self):

        return (
            self.paiements
            .exclude(
                type_paiement='REMBOURSEMENT'
            )
            .aggregate(
                total=Sum('montant')
            )['total']
            or Decimal('0.00')
        )

    # =====================================================
    # TOTAL DES REMBOURSEMENTS
    # =====================================================

    @property
    def total_remboursements(self):

        return (
            self.paiements
            .filter(
                type_paiement='REMBOURSEMENT'
            )
            .aggregate(
                total=Sum('montant')
            )['total']
            or Decimal('0.00')
        )

    # =====================================================
    # TOTAL NET PAYE
    # =====================================================

    @property
    def montant_paye(self):

        montant = (
            self.total_paiements_positifs
            - self.total_remboursements
        )

        if montant < 0:
            return Decimal('0.00')

        return montant

    # =====================================================
    # TOTAL BRUT DES AVANCES
    # =====================================================

    @property
    def total_avances_brut(self):

        return (
            self.paiements
            .filter(
                type_paiement='AVANCE'
            )
            .aggregate(
                total=Sum('montant')
            )['total']
            or Decimal('0.00')
        )

    # =====================================================
    # TOTAL NET DES AVANCES
    # =====================================================

    @property
    def total_avances(self):
        """
        Retourne l'avance encore réellement disponible.

        Exemple :
            Avance : 1000 MAD
            Remboursement : 1000 MAD
            => avance nette : 0 MAD

        Dans le modèle actuel, un remboursement n'est pas
        rattaché à un paiement précis. On considère donc
        les remboursements comme réduisant en priorité
        l'avance disponible.
        """

        avance_nette = (
            self.total_avances_brut
            - self.total_remboursements
        )

        if avance_nette < 0:
            return Decimal('0.00')

        return avance_nette

    # =====================================================
    # RESTE A PAYER
    # =====================================================

    @property
    def reste_a_payer(self):

        reste = (
            self.montant_total
            - self.montant_paye
        )

        if reste < 0:
            return Decimal('0.00')

        return reste

    # =====================================================
    # DOSSIER SOLDE ?
    # =====================================================

    @property
    def est_solde(self):

        if self.montant_total <= 0:
            return False

        return (
            self.montant_paye
            >= self.montant_total
        )

    # =====================================================
    # AVANCE VERSEE ?
    # =====================================================

    @property
    def avance_versee(self):

        return (
            self.total_avances
            > Decimal('0.00')
        )

    # =====================================================
    # PEUT COMMENCER LE TRAITEMENT ?
    # =====================================================

    @property
    def peut_etre_traite(self):

        if self.client.autorise_sans_avance:
            return True

        if not self.avance_requise:
            return True

        return self.avance_versee


class Document(models.Model):

    STATUT_CHOICES = [
        ('RECU', 'Reçu'),
        ('VALIDE', 'Validé'),
        ('MANQUANT', 'Manquant'),
        ('REFUSE', 'Refusé'),
    ]

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='documents'
    )

    ajoute_par = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents_ajoutes'
    )

    nom = models.CharField(
        max_length=150
    )

    fichier = models.FileField(
        upload_to='documents/',
        blank=True,
        null=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='RECU'
    )

    commentaire = models.TextField(
        blank=True,
        null=True
    )

    date_ajout = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nom