from django.db import models
from django.contrib.auth.models import User
from .user_profiles import UserProfile

class Household(models.Model):
    """Représente un ménage (famille, couple, colocation, etc.)"""
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Types de ménages prédéfinis
    HOUSEHOLD_TYPES = [
        ('SINGLE', 'Personne seule'),
        ('COUPLE_SHARED', 'Couple - Tout partagé'),
        ('COUPLE_MIXED', 'Couple - Comptes mixtes'),
        ('COUPLE_SEPARATE', 'Couple - Comptes séparés'),
        ('FAMILY_SHARED', 'Famille - Tout partagé'),
        ('FAMILY_MIXED', 'Famille - Comptes mixtes'),
        ('ROOMMATES', 'Colocation'),
        ('CUSTOM', 'Configuration personnalisée'),
    ]
    
    household_type = models.CharField(
        max_length=20, 
        choices=HOUSEHOLD_TYPES,
        default='SINGLE',
        help_text="Détermine les paramètres de partage par défaut"
    )
    
    def __str__(self):
        return self.name
    
    def apply_sharing_settings(self):
        """Applique les paramètres de partage selon le type de ménage"""
        members = self.members.all()
        
        # Réinitialiser les paramètres
        for member in members:
            profile, _ = UserProfile.objects.get_or_create(user=member.user)
            profile.can_view_all_transactions = False
            profile.can_edit_all_transactions = False
            profile.can_view_all_categories = False
            profile.shared_with_users.clear()
            profile.save()
        
        # Appliquer les paramètres selon le type de ménage
        if self.household_type == 'SINGLE':
            # Rien à faire, tout est personnel
            pass
            
        elif self.household_type == 'COUPLE_SHARED' or self.household_type == 'FAMILY_SHARED':
            # Tout est partagé entre les membres
            for member in members:
                profile, _ = UserProfile.objects.get_or_create(user=member.user)
                other_users = [m.user for m in members if m.user != member.user]
                profile.shared_with_users.add(*other_users)
                profile.save()
                
        elif self.household_type == 'COUPLE_MIXED' or self.household_type == 'FAMILY_MIXED':
            # Seuls les comptes marqués comme partagés sont visibles par tous
            # Cette logique est gérée au niveau des requêtes via le service de permissions
            for member in members:
                profile, _ = UserProfile.objects.get_or_create(user=member.user)
                other_users = [m.user for m in members if m.user != member.user]
                profile.shared_with_users.add(*other_users)
                profile.save()
                
        elif self.household_type == 'COUPLE_SEPARATE' or self.household_type == 'ROOMMATES':
            # Chacun voit uniquement ses propres comptes
            # Mais on peut quand même partager des catégories pour le budget
            for member in members:
                profile, _ = UserProfile.objects.get_or_create(user=member.user)
                profile.can_view_all_categories = True
                profile.save()
                
        elif self.household_type == 'CUSTOM':
            # Configuration personnalisée, ne rien changer automatiquement
            pass

class HouseholdMember(models.Model):
    """Membre d'un ménage avec son rôle"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrateur'),
        ('MEMBER', 'Membre'),
        ('VIEWER', 'Observateur'),
    ]
    
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='households')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='MEMBER')
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['household', 'user']
        
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()}) - {self.household.name}"
