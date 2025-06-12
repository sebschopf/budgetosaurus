# webapp/models/user_profiles.py

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
import pytz

class UserProfile(models.Model):
    """
    Profil utilisateur complet avec fuseau horaire et paramètres de partage
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Paramètres de localisation
    timezone = models.CharField(
        max_length=63,
        choices=[(tz, tz) for tz in pytz.common_timezones],
        default='Europe/Zurich',
        help_text="Votre fuseau horaire préféré pour l'affichage des dates et heures."
    )
    
    # Paramètres de partage
    can_view_all_transactions = models.BooleanField(
        default=False,
        help_text="Peut voir les transactions de tous les utilisateurs"
    )
    can_edit_all_transactions = models.BooleanField(
        default=False,
        help_text="Peut modifier les transactions de tous les utilisateurs"
    )
    can_view_all_categories = models.BooleanField(
        default=False,
        help_text="Peut voir les catégories de tous les utilisateurs"
    )
    
    # Utilisateurs spécifiques avec qui partager
    shared_with_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_access_from',
        help_text="Utilisateurs spécifiques avec qui partager les données"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"

    def __str__(self):
        return f"Profil de {self.user.username}"

# Signal pour créer automatiquement un UserProfile
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # S'assurer que le profil existe même pour les utilisateurs existants
        UserProfile.objects.get_or_create(user=instance)
