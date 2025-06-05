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

# Vous pouvez définir __all__ si vous voulez contrôler ce qui est importé avec '*'
__all__ = [
    'Account',
    'Category',
    'Tag',
    'Transaction',
    'Budget',
    'Fund',
    'FundManager',
    'SavingGoal',
    'CategorizationRule',
    'Allocation',
    'AllocationLine',
]
