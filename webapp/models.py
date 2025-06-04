# webapp/models.py
# Ce fichier contient les définitions de tous les modèles de données pour l'application de budget.

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class Account(models.Model):
    """
    Modèle représentant un compte bancaire ou une source de fonds.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom du compte")
    currency = models.CharField(max_length=3, default='CHF', verbose_name="Devise")
    initial_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Solde initial")

    class Meta:
        # Options de métadonnées pour le modèle
        verbose_name = "Compte Bancaire"
        verbose_name_plural = "Comptes Bancaires"
        ordering = ['name'] # Tri par nom par défaut

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.name} ({self.currency})"

class Category(models.Model):
    """
    Modèle pour les catégories de dépenses/revenus avec une structure parent-enfant.
    Ex: Dépenses Fixes -> Logement -> Loyer
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    parent = models.ForeignKey(
        'self', # Référence à la même classe pour créer une relation parent-enfant
        on_delete=models.SET_NULL, # Si le parent est supprimé, la catégorie devient orpheline (parent=NULL)
        null=True,
        blank=True,
        related_name='children', # Nom d'accès inverse pour obtenir les enfants d'une catégorie
        verbose_name="Catégorie parente"
    )

    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['name']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return self.name

    def clean(self):
        """Valide les données du modèle avant la sauvegarde."""
        # Empêcher une catégorie d'être son propre parent
        if self.parent and self.parent == self:
            raise ValidationError(_("Une catégorie ne peut pas être sa propre parente."))
        # Pour une validation plus complexe des boucles (A -> B -> A), un package comme django-mptt serait utile.

class Transaction(models.Model):
    """
    Modèle représentant une transaction financière (revenu, dépense, transfert).
    """
    TRANSACTION_TYPES = [
        ('IN', 'Revenu'),
        ('OUT', 'Dépense'),
        ('TRF', 'Transfert'), # Utile pour les mouvements entre comptes
    ]

    date = models.DateField(default=timezone.now, verbose_name="Date")
    description = models.CharField(max_length=255, verbose_name="Description")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Montant") # Positif pour revenu, négatif pour dépense
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL, # Si la catégorie est supprimée, la transaction n'aura plus de catégorie
        null=True,
        blank=True,
        related_name='transactions',
        verbose_name="Catégorie"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE, # Si le compte est supprimé, toutes ses transactions le sont aussi
        related_name='transactions',
        verbose_name="Compte"
    )
    transaction_type = models.CharField(
        max_length=3,
        choices=TRANSACTION_TYPES,
        default='OUT',
        verbose_name="Type de transaction"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le") # Date de création automatique
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Mis à jour le") # Date de dernière modification automatique

    class Meta:
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        ordering = ['-date', '-created_at'] # Tri par date descendante, puis par date de création

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.date}: {self.description} ({self.amount} {self.account.currency})"

    def save(self, *args, **kwargs):
        """
        Surcharge de la méthode save pour s'assurer que le montant a le bon signe
        en fonction du type de transaction.
        """
        if self.transaction_type == 'OUT' and self.amount > 0:
            self.amount = -self.amount # Les dépenses sont stockées comme des nombres négatifs
        elif self.transaction_type == 'IN' and self.amount < 0:
            self.amount = abs(self.amount) # Les revenus sont stockés comme des nombres positifs
        super().save(*args, **kwargs)

class Budget(models.Model):
    """
    Modèle pour définir des budgets mensuels ou annuels pour des catégories spécifiques.
    """
    PERIOD_CHOICES = [
        ('M', 'Mensuel'),
        ('Y', 'Annuel'),
    ]

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
    end_date = models.DateField(blank=True, null=True, verbose_name="Date de Fin (optionnel)") # Pour des budgets sur une période définie

    class Meta:
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        # Contrainte unique pour éviter des budgets dupliqués pour la même catégorie/période/date de début
        unique_together = ('category', 'period_type', 'start_date')
        ordering = ['start_date', 'category__name']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"Budget {self.category.name}: {self.amount} ({self.get_period_type_display()})"

    def clean(self):
        """Valide les données du modèle avant la sauvegarde."""
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError(_("La date de fin ne peut pas être antérieure à la date de début."))

class SavingGoal(models.Model):
    """
    Modèle pour suivre les objectifs d'épargne.
    """
    STATUS_CHOICES = [
        ('OU', 'Ouvert'),
        ('AT', 'Atteint'),
        ('AN', 'Annulé'),
    ]

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
        verbose_name_plural = "Objectifs d'Épargne" # Correction de 'verbose_plural_name' à 'verbose_name_plural'
        ordering = ['target_date', 'status']

    def __str__(self):
        """Retourne une représentation en chaîne de caractères de l'objet."""
        return f"{self.name}: {self.current_amount_saved}/{self.target_amount} ({self.get_status_display()})"

