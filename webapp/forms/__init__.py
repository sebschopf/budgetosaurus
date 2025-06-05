# webapp/forms/__init__.py
# Ce fichier rend le dossier 'forms' un paquet Python
# et expose les classes de formulaires pour une importation facile.

from .transaction_form import TransactionForm
from .category_import_form import CategoryImportForm
from .transaction_import_form import TransactionImportForm
from .transaction_split_form import SplitTransactionLineForm, SplitTransactionFormset # Importation des formulaires de division de transaction

__all__ = [
    'TransactionForm', # Formulaire principal de transaction
    'CategoryImportForm', # Formulaire d'importation de catégories
    'TransactionImportForm', # Formulaire d'importation de transactions
    'SplitTransactionLineForm', # Formulaire pour une ligne de division de transaction
    'SplitTransactionFormset', # Formset pour gérer plusieurs lignes de division de transaction
]
