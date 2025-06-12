# webapp/urls.py
from django.urls import path
from webapp.views.dashboard_views import dashboard_view, budget_overview, glossary_view
from webapp.views.summary_views import (
    recap_overview_view,
    category_transactions_summary_view,
    all_transactions_summary_view,
    review_transactions_view
)
from webapp.views.imports import import_transactions_view
from webapp.views.exports import export_transactions_csv
from webapp.views import transaction_actions
from webapp.views.household_views import (
    household_list_view,
    create_household_view,
    household_detail_view,
    add_household_member_view,
    remove_household_member_view,
    change_household_type_view,
    manage_account_sharing_view,
    manage_category_sharing_view,
)

urlpatterns = [
    # Dashboard
    path('', dashboard_view, name='dashboard_view'),
    path('budget-overview/', budget_overview, name='budget_overview'),
    path('glossary/', glossary_view, name='glossary_view'),
    
    # Import/Export
    path('import-transactions/', import_transactions_view, name='import_transactions_view'),
    path('export-transactions-csv/', export_transactions_csv, name='export_transactions_csv'),
    
    # Transaction Actions
    path('get-transaction-form/<int:transaction_id>/', transaction_actions.get_transaction_form, name='get_transaction_form'),
    path('edit-transaction/<int:transaction_id>/', transaction_actions.edit_transaction, name='edit_transaction'),
    path('delete-transaction/<int:transaction_id>/', transaction_actions.delete_transaction, name='delete_transaction'),
    path('delete-selected-transactions/', transaction_actions.delete_selected_transactions, name='delete_selected_transactions'),
    path('suggest-categorization/', transaction_actions.suggest_transaction_categorization, name='suggest_transaction_categorization'),
    
    # Summary Views
    path('recap-overview/', recap_overview_view, name='recap_overview_view'),
    path('category-transactions-summary/', category_transactions_summary_view, name='category_transactions_summary_view'),
    path('category-transactions-summary/<int:year>/', category_transactions_summary_view, name='category_transactions_summary_view'),
    path('category-transactions-summary/<int:year>/<int:month>/', category_transactions_summary_view, name='category_transactions_summary_view'),
    path('all-transactions-summary/', all_transactions_summary_view, name='all_transactions_summary_view'),
    path('review-transactions/', review_transactions_view, name='review_transactions_view'),
    
    # Household Management
    path('households/', household_list_view, name='household_list'),
    path('households/create/', create_household_view, name='create_household'),
    path('households/<int:household_id>/', household_detail_view, name='household_detail'),
    path('households/<int:household_id>/add-member/', add_household_member_view, name='add_household_member'),
    path('households/<int:household_id>/remove-member/<int:user_id>/', remove_household_member_view, name='remove_household_member'),
    path('households/<int:household_id>/change-type/', change_household_type_view, name='change_household_type'),
    path('account-sharing/', manage_account_sharing_view, name='manage_account_sharing'),
    path('category-sharing/', manage_category_sharing_view, name='manage_category_sharing'),
]
