from django.db import models
from dossiers.models import Dossier
from accounts.models import Employe


class Billet(models.Model):

    STATUT_CHOICES = [
        ('EN_ATTENTE', 'En attente'),
        ('RESERVE', 'Réservé'),
        ('BILLET_EMIS', 'Billet émis'),
        ('ANNULE', 'Annulé'),
        ('MODIFIE', 'Modifié'),
    ]

    TYPE_CHOICES = [
        ('AVION', 'Avion'),
        ('TRAIN', 'Train'),
        ('BUS', 'Bus'),
        ('AUTRE', 'Autre'),
    ]

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='billets'
    )

    responsable = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billets_geres'
    )

    type_billet = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='AVION'
    )

    compagnie = models.CharField(max_length=150)
    reference_reservation = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    ville_depart = models.CharField(max_length=100)
    ville_arrivee = models.CharField(max_length=100)

    date_depart = models.DateTimeField()
    date_retour = models.DateTimeField(
        blank=True,
        null=True
    )

    prix = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='EN_ATTENTE'
    )

    commentaire = models.TextField(
        blank=True,
        null=True
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.compagnie} - {self.ville_depart} → {self.ville_arrivee}"