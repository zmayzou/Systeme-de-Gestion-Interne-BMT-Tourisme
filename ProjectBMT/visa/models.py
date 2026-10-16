from django.db import models
from dossiers.models import Dossier
from accounts.models import Employe


class Visa(models.Model):

    STATUT_CHOICES = [
        ('DOCUMENTS_MANQUANTS', 'Documents manquants'),
        ('DOCUMENTS_COMPLETS', 'Documents complets'),
        ('DOSSIER_PRET', 'Dossier prêt'),
        ('DEPOSE', 'Déposé'),
        ('EN_TRAITEMENT', 'En traitement'),
        ('ACCEPTE', 'Accepté'),
        ('REFUSE', 'Refusé'),
    ]

    dossier = models.OneToOneField(
        Dossier,
        on_delete=models.CASCADE,
        related_name='visa'
    )

    responsable = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visas_geres'
    )

    pays_destination = models.CharField(max_length=100)

    type_visa = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default='DOCUMENTS_MANQUANTS'
    )

    date_depot = models.DateField(blank=True, null=True)
    date_rendez_vous = models.DateField(blank=True, null=True)
    date_resultat = models.DateField(blank=True, null=True)

    numero_demande = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    commentaire = models.TextField(
        blank=True,
        null=True
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Visa - {self.dossier.numero_dossier}"