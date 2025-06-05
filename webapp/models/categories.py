# webapp/models/categories.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class Category(models.Model):
    """
    Modèle pour les catégories de dépenses/revenus avec une structure parent-enfant.
    Ajout d'un champ 'is_fund_managed' pour indiquer si cette catégorie doit avoir un fonds dédié.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="Catégorie parente"
    )
    last_used_at = models.DateTimeField(auto_now_add=True, verbose_name="Dernière utilisation")
    #Indique si cette catégorie doit avoir un fonds (une enveloppe) dont le solde est géré.
    is_fund_managed = models.BooleanField(
        default=False,
        verbose_name="Gérer un fonds dédié",
        help_text="Cochez si vous souhaitez gérer un fonds/une enveloppe spécifique pour cette catégorie (solde cumulatif)."
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
        if self.parent and self.parent == self:
            raise ValidationError(_("Une catégorie ne peut pas être sa propre parente."))

