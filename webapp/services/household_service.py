from django.contrib.auth.models import User
from webapp.models import Household, HouseholdMember, UserProfile

class HouseholdService:
    """Service pour gérer les ménages et leurs membres"""
    
    @staticmethod
    def create_household(name, household_type, admin_user):
        """
        Crée un nouveau ménage avec l'utilisateur comme administrateur
        """
        household = Household.objects.create(
            name=name,
            household_type=household_type
        )
        
        # Ajouter l'utilisateur comme administrateur
        HouseholdMember.objects.create(
            household=household,
            user=admin_user,
            role='ADMIN'
        )
        
        # Appliquer les paramètres de partage par défaut
        household.apply_sharing_settings()
        
        return household
    
    @staticmethod
    def add_member(household, user, role='MEMBER'):
        """
        Ajoute un membre au ménage
        """
        member, created = HouseholdMember.objects.get_or_create(
            household=household,
            user=user,
            defaults={'role': role}
        )
        
        if not created:
            member.role = role
            member.save()
        
        # Réappliquer les paramètres de partage
        household.apply_sharing_settings()
        
        return member
    
    @staticmethod
    def remove_member(household, user):
        """
        Retire un membre du ménage
        """
        HouseholdMember.objects.filter(household=household, user=user).delete()
        
        # Réappliquer les paramètres de partage
        household.apply_sharing_settings()
    
    @staticmethod
    def change_household_type(household, new_type):
        """
        Change le type de ménage et réapplique les paramètres de partage
        """
        household.household_type = new_type
        household.save()
        
        # Réappliquer les paramètres de partage
        household.apply_sharing_settings()
    
    @staticmethod
    def get_user_households(user):
        """
        Retourne tous les ménages dont l'utilisateur est membre
        """
        return Household.objects.filter(members__user=user)
    
    @staticmethod
    def get_household_members(household):
        """
        Retourne tous les membres d'un ménage
        """
        return HouseholdMember.objects.filter(household=household).select_related('user')
    
    @staticmethod
    def is_household_admin(user, household):
        """
        Vérifie si l'utilisateur est administrateur du ménage
        """
        return HouseholdMember.objects.filter(
            household=household,
            user=user,
            role='ADMIN'
        ).exists()
