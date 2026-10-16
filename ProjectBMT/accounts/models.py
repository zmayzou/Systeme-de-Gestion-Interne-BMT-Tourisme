from django.db import models
from django.contrib.auth.models import User
from agencies.models import Agence


class PermissionMetier(models.Model):
    nom = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom


class Role(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    permissions = models.ManyToManyField(
        PermissionMetier,
        blank=True,
        related_name='roles'
    )

    def __str__(self):
        return self.nom


class Employe(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employe'
    )

    agence = models.ForeignKey(
        Agence,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes'
    )

    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes'
    )

    permissions_metier = models.ManyToManyField(
        PermissionMetier,
        blank=True,
        related_name='employes'
    )

    telephone = models.CharField(
        max_length=30,
        blank=True,
        null=True
    )

    poste = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    est_actif = models.BooleanField(default=True)

    date_embauche = models.DateField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username