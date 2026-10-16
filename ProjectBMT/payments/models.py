from django.db import models
from dossiers.models import Dossier
from accounts.models import Employe


class Paiement(models.Model):

    TYPE_CHOICES = [
        ('AVANCE', 'Avance'),
        ('PAIEMENT', 'Paiement'),
        ('SOLDE', 'Solde'),
        ('REMBOURSEMENT', 'Remboursement'),
    ]

    MODE_CHOICES = [
        ('ESPECES', 'Espèces'),
        ('CARTE', 'Carte bancaire'),
        ('VIREMENT', 'Virement'),
        ('CHEQUE', 'Chèque'),
        ('AUTRE', 'Autre'),
    ]

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='paiements'
    )

    enregistre_par = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements_enregistres'
    )

    type_paiement = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )

    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='ESPECES'
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    commentaire = models.TextField(
        blank=True,
        null=True
    )

    date_paiement = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type_paiement} - {self.montant} MAD"