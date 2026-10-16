from django.db import models
from accounts.models import Employe
from dossiers.models import Dossier


class Guide(models.Model):

    employe = models.OneToOneField(
        Employe,
        on_delete=models.CASCADE,
        related_name='profil_guide'
    )

    langues = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    specialite = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    est_disponible = models.BooleanField(default=True)

    def __str__(self):
        return str(self.employe)


class MissionGuide(models.Model):

    STATUT_CHOICES = [
        ('PLANIFIEE', 'Planifiée'),
        ('EN_COURS', 'En cours'),
        ('TERMINEE', 'Terminée'),
        ('ANNULEE', 'Annulée'),
    ]

    guide = models.ForeignKey(
        Guide,
        on_delete=models.CASCADE,
        related_name='missions'
    )

    dossier = models.ForeignKey(
        Dossier,
        on_delete=models.CASCADE,
        related_name='missions_guides'
    )

    lieu = models.CharField(max_length=150)

    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='PLANIFIEE'
    )

    commentaire = models.TextField(
        blank=True,
        null=True
    )

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.guide} - {self.lieu}"