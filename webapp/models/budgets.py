# webapp/models/budgets.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
# Importez les modèles depuis le même paquet 'models'
from .categories import Category
from django.contrib.auth.models import User

class Budget(models.Model):
    """
    Modèle pour définir des budgets mensuels ou annuels pour des catégories spécifiques.
    Ce modèle peut être utilisé pour la planification des contributions mensuelles aux fonds.
    """
    PERIOD_CHOICES = [
        ('M', 'Mensuel'),
        ('Y', 'Annuel'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets', verbose_name="Utilisateur")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name="Catégorie"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant Budgété")
    period_type = models.CharField(
        max_length=1,
        choices=PERIOD_CHOICES,
        default='M',
        verbose_name="Type de Période"
    )
    start_date = models.DateField(verbose_name="Date de Début")
    end_date = models.DateField(blank=True, null=True, verbose_name="Date de Fin (optionnel)")

    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        unique_together = ('user', 'category', 'period_type', 'start_date') # Rend la combinaison unique par utilisateur
        ordering = ['start_date', 'category__name']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"Budget {self.category.name}: {self.amount} ({self.get_period_type_display()})"

    def clean(self):
        """Valide les données du modèle avant la sauvegarde."""
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError(_("La date de fin ne peut pas être antérieure à la date de début."))
