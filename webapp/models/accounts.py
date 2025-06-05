# webapp/models/accounts.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Account(models.Model):
    """
    Modèle représentant un compte bancaire ou une source de fonds.
    Ajout d'un champ 'account_type' pour mieux définir la nature du compte.
    """
    ACCOUNT_TYPES = [
        ('INDIVIDUAL', 'Individuel'),
        ('COMMON', 'Commun'),
        ('SAVINGS', 'Épargne'),
        ('OTHER', 'Autre'), # Pour les cas non couverts
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du compte")
    currency = models.CharField(max_length=3, default='CHF', verbose_name="Devise")
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Solde initial")
    account_type = models.CharField(
        max_length=10,
        choices=ACCOUNT_TYPES,
        default='INDIVIDUAL', # Valeur par défaut
        verbose_name="Type de compte",
        help_text="Définissez si ce compte est individuel, commun, d'épargne, etc."
    )

    class Meta:
        verbose_name = "Compte Bancaire"
        verbose_name_plural = "Comptes Bancaires"
        ordering = ['name']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.name} ({self.currency}) - {self.get_account_type_display()}"
