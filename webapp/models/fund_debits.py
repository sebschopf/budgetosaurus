# webapp/models/fund_debits.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .transactions import Transaction
from .categories import Category
from django.contrib.auth.models import User

class FundDebitRecord(models.Model):
    """
    Modèle représentant une opération de débit d'une transaction de dépense
    vers plusieurs fonds budgétaires.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fund_debit_records',
        verbose_name="Utilisateur",
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name='fund_debit_record', # Renommer la relation inverse pour éviter les conflits
        verbose_name="Transaction de dépense associée",
        help_text="La transaction de dépense qui est débitée des fonds."
    )
    total_debited_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0.00,
        verbose_name="Montant total débité des fonds",
        help_text="La somme des montants débités des fonds."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes sur le débit de fonds",
        help_text="Détails ou commentaires sur cette opération de débit."
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    class Meta:
        verbose_name = "Débit de Fonds"
        verbose_name_plural = "Débits de Fonds"
        ordering = ['-created_at']
        # une opération de débit est déjà unique par transaction via la relation OneToOneField

    def __str__(self):
        return f"Débit de fonds pour transaction {self.transaction.id} ({self.transaction.description}) - {self.total_debited_amount} CHF"

class FundDebitLine(models.Model):
    """
    Modèle représentant une ligne individuelle au sein d'une opération de débit de fonds,
    spécifiant le montant débité d'une catégorie de fonds spécifique.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fund_debit_lines_by_user',
        verbose_name="Utilisateur",
    )
    fund_debit_record = models.ForeignKey(
        FundDebitRecord,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name="Enregistrement de débit de fonds parent"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE, # Si la catégorie est supprimée, la ligne de débit est supprimée
        related_name='fund_debit_lines',
        verbose_name="Catégorie de fonds"
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Montant débité",
        help_text="Le montant débité de cette catégorie de fonds."
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes de ligne",
        help_text="Notes spécifiques à cette ligne de débit."
    )

    class Meta:
        verbose_name = "Ligne de Débit de Fonds"
        verbose_name_plural = "Lignes de Débit de Fonds"
        unique_together = ('fund_debit_record', 'category') # Une catégorie ne peut être débitée qu'une fois par enregistrement de débit
        ordering = ['category__name']

    def __str__(self):
        return f"Ligne de débit: {self.amount} CHF de {self.category.name}"

