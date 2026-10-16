from django.db import models
from accounts.models import Employe


class Notification(models.Model):

    employe = models.ForeignKey(
        Employe,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    titre = models.CharField(max_length=150)
    message = models.TextField()

    est_lue = models.BooleanField(default=False)

    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre
class HistoriqueAction(models.Model):

    employe = models.ForeignKey(
        Employe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='actions_historique'
    )

    action = models.CharField(max_length=200)

    module = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    objet_id = models.PositiveIntegerField(
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    date_action = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.date_action}"