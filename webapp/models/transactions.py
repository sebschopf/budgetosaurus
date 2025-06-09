# webapp/models/transactions.py
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
# Importez les modèles depuis le même paquet 'models'
from .categories import Category
from .accounts import Account
from .tags import Tag
from django.contrib.auth.models import User

class Transaction(models.Model):
    """
    Modèle représentant une transaction financière (revenu, dépense, transfert).
    La logique de normalisation du montant est gérée par un signal pre_save.
    """
    TRANSACTION_TYPES = [
        ('IN', 'Revenu'),
        ('OUT', 'Dépense'),
        ('TRF', 'Transfert'), # Utile pour les mouvements entre comptes
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions', verbose_name="Utilisateur")
    date = models.DateField(default=timezone.now, verbose_name="Date")
    description = models.CharField(max_length=255, verbose_name="Description")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant") # Positif pour revenu, négatif pour dépense
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Catégorie"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name="Compte"
    )
    transaction_type = models.CharField(
        max_length=3,
        choices=TRANSACTION_TYPES,
        default='OUT',
        verbose_name="Type de transaction"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='transactions', verbose_name="Tags")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le")

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-date', '-created_at']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.date}: {self.description} ({self.amount} {self.account.currency})"
