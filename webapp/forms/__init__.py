# webapp/forms/__init__.py
# Ce fichier rend le dossier 'forms' un paquet Python
# et expose les classes de formulaires pour une importation facile.

from .transaction_form import TransactionForm
from .category_import_form import CategoryImportForm
from .transaction_import_form import TransactionImportForm
from .transaction_split_form import SplitTransactionLineForm, SplitTransactionFormset # Importation des formulaires de division de transaction
from .allocation_forms import AllocationForm, AllocationLineForm, AllocationLineFormset # Formulaires d'allocation
from .fund_debit_forms import FundDebitRecordForm, FundDebitLineForm, FundDebitLineFormset # formulaires de débit de fonds

__all__ = [
    # Formulaires de transaction
    'TransactionForm', # principal
    'CategoryImportForm', # importation de catégories
    'TransactionImportForm', # importation
    'SplitTransactionLineForm', # une ligne de division
    'SplitTransactionFormset', # Formset pour gérer plusieurs lignes de division

    # Formulaires d'allocation
    'AllocationForm', # principal
    'AllocationLineForm', # une ligne d'allocation
    'AllocationLineFormset', # Formset pour gérer plusieurs lignes

    # Formulaires de débit de fonds
    'FundDebitRecordForm', # Formulaire principal de débit de fonds
    'FundDebitLineForm', # Formulaire pour une ligne de débit de fonds
    'FundDebitLineFormset', # Formset pour gérer plusieurs lignes de débit de fonds
]

