# webapp/models/user_profile.py

from django.db import models
from django.contrib.auth.models import User # Importez le modèle User de Django
import pytz # Importez pytz pour la liste des fuseaux horaires

class UserProfile(models.Model):
    """
    Modèle de profil utilisateur pour stocker des informations spécifiques à l'utilisateur,
    comme son fuseau horaire préféré.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    timezone = models.CharField(
        max_length=63,
        choices=[(tz, tz) for tz in pytz.common_timezones], # Liste de tous les fuseaux horaires courants
        default='Europe/Zurich', # Définissez une valeur par défaut appropriée pour votre région (par exemple, 'UTC' si vous préférez)
        help_text="Votre fuseau horaire préféré pour l'affichage des dates et heures."
    )

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"

    def __str__(self):
        return f"Profil de {self.user.username}"

# Cette partie assure qu'un UserProfile est créé ou mis à jour
# automatiquement chaque fois qu'un objet User est sauvegardé.
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        # Crée un UserProfile pour le nouvel utilisateur
        UserProfile.objects.create(user=instance)
    # Assure que le profil existant est sauvegardé si l'utilisateur est mis à jour
    # Cela est important pour le cas où le signal est déclenché par une mise à jour de l'utilisateur
    instance.profile.save()