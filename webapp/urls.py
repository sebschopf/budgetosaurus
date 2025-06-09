# webapp/urls.py
# Ce fichier définit les chemins d'URL pour les vues de l'application 'webapp'.

from django.urls import path, re_path # re_path pour les regex dans les URLs
# Importe les vues directement depuis leurs modules refactorisés
from .views import (
    general_transactions,
    transaction_actions,
    summary_views,
    split_transactions_views,
    fund_allocations_views,
    fund_debits_views,
    imports, # Cette vue est importante
    budgets,
    review_transactions,
    glossary
)

urlpatterns = [
    # URL de la page d'accueil/tableau de bord
    path('', general_transactions.dashboard_view, name='dashboard_view'),

    # URL pour la soumission du formulaire d'ajout de transaction (POST seulement)
    path('add-transaction-submit/', general_transactions.add_transaction_submit, name='add_transaction_submit'),

    # URL pour la requête AJAX de chargement des sous-catégories
    path('load-subcategories/', general_transactions.load_subcategories, name='load_subcategories'),

    # URL pour récupérer les descriptions de transactions courantes (pour l'autocomplétion)
    path('get-common-descriptions/', general_transactions.get_common_descriptions, name='get_common_descriptions'),

    # URL pour la page d'importation des transactions via CSV
    path('import-transactions/', imports.import_transactions_view, name='import_transactions_view'),

    # URL pour l'importation des catégories (manquait le name)
    path('import-categories/', imports.import_categories, name='import_categories'),

    # URL pour la page de l'aperçu des budgets
    path('budget-overview/', budgets.budget_overview, name='budget_overview'),

    # URLs pour la révision des transactions
    path('review-transactions/', review_transactions.review_transactions_view, name='review_transactions_view'),
    path('update-transaction-category/<int:transaction_id>/', review_transactions.update_transaction_category, name='update_transaction_category'),

    # URL pour obtenir le formulaire d'édition de transaction via AJAX
    path('get-transaction-form/<int:transaction_id>/', transaction_actions.get_transaction_form_for_edit, name='get_transaction_form_for_edit'),

    # URL pour la suppression par lot des transactions
    path('delete-selected-transactions/', transaction_actions.delete_selected_transactions, name='delete_selected_transactions'),

    # URL pour le glossaire
    path('glossary/', glossary.glossary_view, name='glossary_view'),

    # URL pour la suggestion de catégorisation via AJAX (Fuzzy Matching)
    path('suggest-categorization/', transaction_actions.suggest_transaction_categorization, name='suggest_transaction_categorization'),

    # URL pour la page d'aperçu des différents récapitulatifs et outils de gestion.
    path('recap-overview/', summary_views.recap_overview_view, name='recap_overview_view'),

    # URLs pour le récapitulatif des transactions par catégorie avec filtres de période
    re_path(r'^category-transactions-summary/(?:(?P<year>\d{4})/)?(?:(?P<month>\d{1,2})/)?$',
            summary_views.category_transactions_summary_view,
            name='category_transactions_summary_view'),

    # URL pour le récapitulatif de toutes les transactions
    path('all-transactions-summary/', summary_views.all_transactions_summary_view, name='all_transactions_summary_view'),

    # URLs pour la fonctionnalité de division de transaction
    path('split-transaction/<int:transaction_id>/', split_transactions_views.split_transaction_view, name='split_transaction_view_with_id'),
    path('split-transaction/', split_transactions_views.split_transaction_view, name='split_transaction_view'), # Pour la vue sans ID initial
    path('process-split-transaction/', split_transactions_views.process_split_transaction, name='process_split_transaction'), # URL pour le POST du split

    # URLs pour l'allocation de revenu
    path('allocate-income/<int:transaction_id>/', fund_allocations_views.allocate_income_view, name='allocate_income_view'),
    path('process-allocation-income/<int:transaction_id>/', fund_allocations_views.process_allocation_income, name='process_allocation_income'),

    # URLs pour le débit de fonds
    path('debit-funds/<int:transaction_id>/', fund_debits_views.debit_funds_view, name='debit_funds_view'),
    path('process-fund-debit/<int:transaction_id>/', fund_debits_views.process_fund_debit, name='process_fund_debit'),
]
