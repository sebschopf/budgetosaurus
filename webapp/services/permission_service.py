from django.contrib.auth.models import User
from django.db.models import Q
from webapp.models import UserProfile, Transaction, Category, Account, Household, HouseholdMember

class PermissionService:
    """Service pour gérer les permissions de partage entre utilisateurs"""
    
    @staticmethod
    def get_user_profile(user):
        """Récupère ou crée le profil utilisateur"""
        profile, created = UserProfile.objects.get_or_create(user=user)
        return profile
    
    @staticmethod
    def get_user_households(user):
        """Récupère les ménages de l'utilisateur"""
        return Household.objects.filter(members__user=user)
    
    @staticmethod
    def get_household_members(user):
        """Récupère les membres des ménages de l'utilisateur"""
        households = PermissionService.get_user_households(user)
        return User.objects.filter(households__household__in=households).distinct().exclude(id=user.id)
    
    @staticmethod
    def get_accessible_transactions(user):
        """
        Retourne les transactions accessibles à l'utilisateur selon les règles:
        1. Ses propres transactions
        2. Transactions des comptes partagés de son ménage
        3. Transactions explicitement partagées
        4. Toutes les transactions s'il a la permission globale
        """
        profile = PermissionService.get_user_profile(user)
        
        if user.is_superuser or profile.can_view_all_transactions:
            # Administrateur ou permission globale
            return Transaction.objects.all()
        
        # Récupérer les membres des ménages de l'utilisateur
        household_members = PermissionService.get_household_members(user)
        
        # Construire la requête pour les transactions accessibles
        query = Q(user=user)  # Ses propres transactions
        
        if household_members.exists():
            # Transactions des comptes partagés des membres du ménage
            query |= Q(
                user__in=household_members,
                account__is_shared=True
            )
            
            # Transactions explicitement partagées
            query |= Q(
                user__in=household_members,
                is_shared=True
            )
            
            # Utilisateurs qui ont explicitement partagé avec cet utilisateur
            shared_with_users = list(profile.shared_with_users.all())
            if shared_with_users:
                query |= Q(user__in=shared_with_users)
        
        return Transaction.objects.filter(query)
    
    @staticmethod
    def get_accessible_accounts(user):
        """
        Retourne les comptes accessibles à l'utilisateur:
        1. Ses propres comptes
        2. Comptes partagés des membres de son ménage
        3. Tous les comptes s'il a la permission globale
        """
        profile = PermissionService.get_user_profile(user)
        
        if user.is_superuser or profile.can_view_all_transactions:
            return Account.objects.all()
        
        # Récupérer les membres des ménages de l'utilisateur
        household_members = PermissionService.get_household_members(user)
        
        # Construire la requête pour les comptes accessibles
        query = Q(user=user)  # Ses propres comptes
        
        if household_members.exists():
            # Comptes partagés des membres du ménage
            query |= Q(
                user__in=household_members,
                is_shared=True
            )
        
        return Account.objects.filter(query)
    
    @staticmethod
    def get_accessible_categories(user):
        """
        Retourne les catégories accessibles à l'utilisateur:
        1. Ses propres catégories
        2. Catégories partagées des membres de son ménage
        3. Toutes les catégories s'il a la permission globale
        """
        profile = PermissionService.get_user_profile(user)
        
        if user.is_superuser or profile.can_view_all_categories:
            return Category.objects.all()
        
        # Récupérer les membres des ménages de l'utilisateur
        household_members = PermissionService.get_household_members(user)
        
        # Construire la requête pour les catégories accessibles
        query = Q(user=user)  # Ses propres catégories
        
        if household_members.exists():
            # Catégories partagées des membres du ménage
            query |= Q(
                user__in=household_members,
                is_shared=True
            )
        
        return Category.objects.filter(query)
    
    @staticmethod
    def can_edit_transaction(user, transaction):
        """
        Vérifie si l'utilisateur peut modifier une transaction:
        1. Si c'est sa propre transaction
        2. Si la transaction est dans un compte partagé et l'utilisateur est admin du ménage
        3. Si l'utilisateur a la permission globale d'édition
        """
        if user.is_superuser:
            return True
        
        if transaction.user == user:
            return True
        
        profile = PermissionService.get_user_profile(user)
        if profile.can_edit_all_transactions:
            return True
        
        # Vérifier si l'utilisateur est admin d'un ménage commun avec le propriétaire
        user_households = Household.objects.filter(members__user=user, members__role='ADMIN')
        transaction_owner_in_same_household = HouseholdMember.objects.filter(
            user=transaction.user,
            household__in=user_households
        ).exists()
        
        # Si le compte est partagé et l'utilisateur est admin du ménage
        if transaction.account.is_shared and transaction_owner_in_same_household:
            return True
        
        # Si la transaction est explicitement partagée et l'utilisateur est admin du ménage
        if transaction.is_shared and transaction_owner_in_same_household:
            return True
        
        return False
