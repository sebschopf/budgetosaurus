# webapp/models/__init__.py
# Ce fichier rend le dossier 'models' un paquet Python
# et importe tous les modèles pour un accès facile depuis 'webapp.models'.

from .accounts import Account
from .categories import Category
from .tags import Tag
from .transactions import Transaction
from .budgets import Budget
from .funds import Fund, FundManager
from .saving_goals import SavingGoal
from .categorization_rules import CategorizationRule
from .allocations import Allocation, AllocationLine # Nouveaux modèles d'allocation
from .fund_debits import FundDebitRecord, FundDebitLine # Nouveaux modèles de débits de fonds
from .user_profile import UserProfile # Modèle pour le profil utilisateur

#  __all__  pour ce qui est importé avec '*'
__all__ = [
    'Account', # compte bancaire
    'Category', # catégorie principale
    'Tag', # étiquette
    'Transaction', # transaction principale
    'Budget', # budget
    'Fund', # fonds (enveloppes budgétaires)
    'FundManager', # gestionnaire de fonds
    'SavingGoal', # objectif d'épargne
    'CategorizationRule', # catégorisation automatique
    'Allocation', # allocation
    'AllocationLine', # allocation line
    'FundDebitRecord', # fond debit record
    'FundDebitLine',   # fond debit line
    'UserProfile'  # profil utilisateur	
]

