# webapp/models/allocations.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .transactions import Transaction
from .categories import Category
from django.contrib.auth.models import User

class Allocation(models.Model):
    """
    Modèle représentant une opération de ventilation d'une transaction de revenu
    (généralement un revenu sur un compte commun) vers plusieurs fonds budgétaires.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name="Utilisateur",
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='allocation',
        verbose_name="Transaction de revenu associée",
        help_text="La transaction de revenu (ex: virement salarial) qui est ventilée."
    )
    total_allocated_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Montant total alloué",
        help_text="La somme des montants alloués aux fonds."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes sur l'allocation",
        help_text="Détails ou commentaires sur cette opération de ventilation."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    class Meta:
        verbose_name = "Allocation de Fonds"
        verbose_name_plural = "Allocations de Fonds"
        ordering = ['-created_at']
        # une alloncation est déjà unique par transaction via la relation OneToOneField
    def __str__(self):
        return f"Allocation pour transaction {self.transaction.id} ({self.transaction.description}) - {self.total_allocated_amount} CHF"

class AllocationLine(models.Model):
    """
    Modèle représentant une ligne individuelle au sein d'une opération d'allocation,
    spécifiant le montant alloué à une catégorie de fonds spécifique.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='allocation_lines_by_user',
        verbose_name="Utilisateur",
    )

    allocation = models.ForeignKey(
        Allocation,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Allocation parente"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE, # Si la catégorie est supprimée, la ligne d'allocation est supprimée
        related_name='allocation_lines',
        verbose_name="Catégorie de fonds"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Montant alloué",
        help_text="Le montant alloué à cette catégorie de fonds."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes de ligne",
        help_text="Notes spécifiques à cette ligne d'allocation."
    )

    class Meta:
        verbose_name = "Ligne d'Allocation"
        verbose_name_plural = "Lignes d'Allocation"
        unique_together = ('allocation', 'category') # Une catégorie ne peut être allouée qu'une fois par allocation
        ordering = ['category__name']

    def __str__(self):
        return f"Ligne d'allocation: {self.amount} CHF vers {self.category.name}"
