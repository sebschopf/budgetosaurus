# webapp/models/categorization_rules.py
from django.db import models
from django.utils.translation import gettext_lazy as _
# Importez les modèles depuis le même paquet 'models'
from .categories import Category
from .tags import Tag
from django.contrib.auth.models import User

class CategorizationRule(models.Model):
    """
    Modèle pour stocker les règles d'apprentissage pour la catégorisation automatique
    des transactions basées sur leur description.
    """
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='categorization_rules',
        verbose_name="Utilisateur")

    description_pattern = models.CharField(
        max_length=255,
        unique=True, # Une seule règle par description exacte
        verbose_name="Modèle de description"
    )
    suggested_category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='categorization_rules',
        verbose_name="Catégorie suggérée"
    )
    suggested_tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name='categorization_rules',
        verbose_name="Tags suggérés"
    )
    last_applied_at = models.DateTimeField(
        auto_now=True, # Met à jour la date à chaque modification
        verbose_name="Dernière application"
    )
    hit_count = models.IntegerField(
        default=1,
        verbose_name="Nombre d'occurrences"
    )

    class Meta:
        verbose_name = "Règle de Catégorisation"
        verbose_name_plural = "Règles de Catégorisation"
        ordering = ['-hit_count', '-last_applied_at'] # Les règles les plus utilisées/récentes en premier
        unique_together = ('user', 'description_pattern')   # Assure que le modèle de description est unique par utilisateur

    def __str__(self):
        return f"Règle pour '{self.description_pattern}' -> Cat: {self.suggested_category.name if self.suggested_category else 'N/A'}"
