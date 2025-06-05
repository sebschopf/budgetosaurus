# webapp/models/tags.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Tag(models.Model):
    """
    Modèle pour les tags (étiquettes) qui peuvent être associés aux transactions
    pour une classification et une analyse transversale plus flexibles.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Nom du Tag")
    description = models.TextField(blank=True, verbose_name="Description du Tag")
    last_used_at = models.DateTimeField(auto_now_add=True, verbose_name="Dernière utilisation")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ['name']

    def __str__(self):
        return self.name
