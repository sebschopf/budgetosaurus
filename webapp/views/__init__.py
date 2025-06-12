# webapp/views/__init__.py
# Ce fichier permet d'importer les vues depuis les sous-modules

from . import summary_views
from . import transaction_actions
from . import exports

# Exposer les vues principales pour faciliter l'import
from .summary_views import (
    recap_overview_view,
    category_transactions_summary_view,
    all_transactions_summary_view,
    review_transactions_view
)

from .transaction_actions import (
    get_transaction_form,
    edit_transaction,
    delete_transaction,
    delete_selected_transactions
)

from .exports import export_transactions_csv
