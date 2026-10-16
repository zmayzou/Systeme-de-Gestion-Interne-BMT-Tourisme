from django.db import models

from agencies.models import Agence
from accounts.models import Employe


class Client(models.Model):

    TYPE_CLIENT_CHOICES = [
        ('NOUVEAU', 'Nouveau'),
        ('FIDELE', 'Fidèle'),
    ]

    agence = models.ForeignKey(
        Agence,
        on_delete=models.PROTECT,
        related_name='clients',
        null=True,
        blank=True
    )

    cree_par = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clients_crees'
    )

    nom = models.CharField(
        max_length=100
    )

    prenom = models.CharField(
        max_length=100
    )

    cin = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        null=True
    )

    passeport = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True
    )

    telephone = models.CharField(
        max_length=30
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    adresse = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    type_client = models.CharField(
        max_length=20,
        choices=TYPE_CLIENT_CHOICES,
        default='NOUVEAU'
    )

    autorise_sans_avance = models.BooleanField(
        default=False
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    date_modification = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.nom} {self.prenom}"