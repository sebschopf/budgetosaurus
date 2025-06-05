# webapp/urls.py
# Ce fichier définit les chemins d'URL pour les vues de l'application 'webapp'.

from django.urls import path
# Importe les vues directement depuis leurs modules
from .views import dashboard, transactions, imports, budgets, review_transactions, glossary 

urlpatterns = [
    # URL de la page d'accueil/tableau de bord
    path('', dashboard.dashboard_view, name='dashboard_view'),
    
    # URL pour la soumission du formulaire d'ajout de transaction (POST seulement)
    path('add-transaction-submit/', transactions.add_transaction_submit, name='add_transaction_submit'),
    
    # URL pour la requête AJAX de chargement des sous-catégories
    path('load-subcategories/', transactions.load_subcategories, name='load_subcategories'),
    
    # URL pour récupérer les descriptions de transactions courantes (pour l'autocomplétion)
    path('get-common-descriptions/', transactions.get_common_descriptions, name='get_common_descriptions'),

    # URL pour la page d'importation des transactions via CSV
    path('import-transactions/', imports.import_transactions_view, name='import_transactions_view'),

    # URL pour la page de l'aperçu des budgets
    path('budget-overview/', budgets.budget_overview, name='budget_overview'),

    # URLs pour la révision des transactions
    path('review-transactions/', review_transactions.review_transactions_view, name='review_transactions_view'),
    path('update-transaction-category/<int:transaction_id>/', review_transactions.update_transaction_category, name='update_transaction_category'),
    
    # URL pour obtenir le formulaire d'édition de transaction via AJAX
    path('get-transaction-form/<int:transaction_id>/', transactions.get_transaction_form_for_edit, name='get_transaction_form_for_edit'),

    # URL pour la suppression par lot des transactions
    path('delete-selected-transactions/', transactions.delete_selected_transactions, name='delete_selected_transactions'),

    # URL pour le glossaire
    path('glossary/', glossary.glossary_view, name='glossary_view'),

    # Nouvelle URL pour la suggestion de catégorisation via AJAX (Fuzzy Matching)
    path('suggest-categorization/', transactions.suggest_transaction_categorization, name='suggest_transaction_categorization'),
]
