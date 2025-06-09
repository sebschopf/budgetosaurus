# webapp/models/funds.py
from django.db import models
from django.utils.translation import gettext_lazy as _
# Importez les modèles depuis le même paquet 'models'
from .categories import Category
from django.contrib.auth.models import User

class FundManager(models.Manager):
    """
    Manager personnalisé pour le modèle Fund, encapsulant la logique métier
    d'ajout et de soustraction de fonds.
    """
    def get_queryset(self):
        """
        Retourne le queryset de base pour le modèle Fund.
        Peut être étendu pour inclure des filtres ou des annotations spécifiques.
        """
        return super().get_queryset()
    
    def add_funds_to_category(self, category, amount, user):
        """
        Ajoute des fonds à un fonds lié à une catégorie spécifique.
        Crée le fonds s'il n'existe pas.
        """
        fund, created = self.get_or_create(category=category, user=user)
        fund.current_balance += amount
        fund.save()
        return fund

    def subtract_funds_from_category(self, category, amount, user):
        """
        Soustrait des fonds d'un fonds lié à une catégorie spécifique.
        Crée le fonds s'il n'existe pas.
        """
        fund, created = self.get_or_create(category=category, user=user)
        fund.current_balance -= amount
        fund.save()
        return fund

class Fund(models.Model):
    """
    Représente un fonds budgétaire virtuel pour une catégorie donnée,
    permettant de suivre les fonds alloués et disponibles pour cette catégorie.
    Ceci est le "compte virtuel" que l'utilisateur souhaite suivre.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='funds', verbose_name="Utilisateur")  
    category = models.OneToOneField(
        Category,
        on_delete=models.CASCADE,
        related_name='fund',
        verbose_name="Catégorie de fonds"
    )
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0.00,
                                         verbose_name="Solde actuel du fonds")
    last_updated = models.DateTimeField(auto_now=True)

    objects = FundManager() # Attache le manager personnalisé ici

    class Meta:
        verbose_name = "Fonds Budgétaire"
        verbose_name_plural = "Fonds Budgétaires"
        ordering = ['category__name']
        unique_together = ('user', 'category')  # Assure que chaque utilisateur n'a qu'un seul fonds par catégorie

    def __str__(self):
        return f"Fonds '{self.category.name}': {self.current_balance} CHF"
