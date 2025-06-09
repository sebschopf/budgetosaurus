# webapp/models/saving_goals.py
from django.db import models
from django.utils.translation import gettext_lazy as _
# Importez les modèles depuis le même paquet 'models'
from .categories import Category
from django.contrib.auth.models import User

class SavingGoal(models.Model):
    """
    Modèle pour suivre les objectifs d'épargne.
    """
    STATUS_CHOICES = [
        ('OU', 'Ouvert'),
        ('AT', 'Atteint'),
        ('AN', 'Annulé'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saving_goals', verbose_name="Utilisateur")
    name = models.CharField(max_length=100, verbose_name="Nom de l'objectif")
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='saving_goals',
        verbose_name="Catégorie liée (optionnel)"
    )
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant Cible")
    current_amount_saved = models.DecimalField(max_digits=10, decimal_places=2, default=0.0, verbose_name="Montant Actuel Mis de Côté")
    target_date = models.DateField(verbose_name="Date Cible")
    status = models.CharField(
        max_length=2,
        choices=STATUS_CHOICES,
        default='OU',
        verbose_name="Statut"
    )
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Objectif d'Épargne"
        verbose_name_plural = "Objectifs d'Épargne"
        ordering = ['target_date', 'status']
        unique_together = ('user', 'name')  # Assure que le nom de l'objectif est unique par utilisateur

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.name}: {self.current_amount_saved}/{self.target_amount} ({self.get_status_display()})"
