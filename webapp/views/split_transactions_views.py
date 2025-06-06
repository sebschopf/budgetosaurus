# webapp/views/split_transactions_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from decimal import Decimal
from datetime import date 

from webapp.models import Transaction, Category, Budget, SavingGoal # NOUVEAU: Importez SavingGoal
from webapp.forms import SplitTransactionFormset
from webapp.services import TransactionService

@require_GET
def split_transaction_view(request, transaction_id=None):
    original_transaction = None
    formset = SplitTransactionFormset() 

    if transaction_id:
        original_transaction = get_object_or_404(Transaction, pk=transaction_id)
        if original_transaction.transaction_type == 'OUT': 
            initial_data = []
            initial_data.append({
                'description': original_transaction.description,
                'amount': abs(original_transaction.amount),
                'main_category': original_transaction.category.parent.id if original_transaction.category and original_transaction.category.parent else (original_transaction.category.id if original_transaction.category else None),
                'subcategory': original_transaction.category.id if original_transaction.category and original_transaction.category.parent else None,
            })
            formset = SplitTransactionFormset(initial=initial_data)

    all_categories_data = []
    all_subcategories_data = []

    current_year = date.today().year
    current_month = date.today().month
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            period_type='M', 
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    # NOUVEAU: Préparez un ensemble des IDs de catégories liées à des objectifs d'épargne
    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            status='OU' # Seulement les objectifs ouverts/actifs
        ).values_list('category__id', flat=True)
    )

    for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
        is_budgeted_for_display = cat.is_budgeted 
        is_fund_managed_for_display = cat.is_fund_managed
        is_goal_linked_for_display = cat.id in goal_linked_category_ids

        all_categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': is_fund_managed_for_display,
            'is_budgeted': is_budgeted_for_display,
            'is_goal_linked': is_goal_linked_for_display 
        })
        for child_cat in cat.children.all().order_by('name'):
            child_is_budgeted_for_display = child_cat.is_budgeted
            child_is_fund_managed_for_display = child_cat.is_fund_managed
            child_is_goal_linked_for_display = child_cat.id in goal_linked_category_ids

            all_subcategories_data.append({
                'id': child_cat.id,
                'name': child_cat.name,
                'parent': cat.id,
                'is_fund_managed': child_is_fund_managed_for_display,
                'is_budgeted': child_is_budgeted_for_display,
                'is_goal_linked': child_is_goal_linked_for_display
            })
    
    context = {
        'page_title': 'Diviser une Transaction',
        'original_transaction': original_transaction,
        'formset': formset,
        'all_categories_data_json': json.dumps(all_categories_data), 
        'all_subcategories_data_json': json.dumps(all_subcategories_data), 
    }
    return render(request, 'webapp/split_transaction.html', context)

@require_POST
def process_split_transaction(request):
    original_transaction_id = request.POST.get('original_transaction_id')
    original_transaction = get_object_or_404(Transaction, pk=original_transaction_id)

    formset = SplitTransactionFormset(request.POST)
    transaction_service = TransactionService()

    if formset.is_valid():
        split_lines_data = []
        for form in formset:
            if not form.cleaned_data.get('DELETE', False): 
                final_category = form.cleaned_data.get('final_category')
                if not final_category: 
                    messages.error(request, "Une catégorie valide est requise pour chaque ligne de division non supprimée.")
                    return _render_split_transaction_page_with_errors(request, original_transaction, formset)

                split_lines_data.append({
                    'description': form.cleaned_data['description'],
                    'amount': form.cleaned_data['amount'],
                    'category': final_category,
                    'tags': [], 
                })
        
        try:
            transaction_service.split_transaction(original_transaction, split_lines_data)
            messages.success(request, "Transaction divisée et enregistrée avec succès!")
            return redirect('all_transactions_summary_view')
        except ValueError as e:
            messages.error(request, f"Erreur de division: {e}")
        except Exception as e:
            messages.error(request, f"Erreur inattendue lors de la division: {e}")
    else:
        messages.error(request, "Veuillez corriger les erreurs dans le formulaire de division.")
    
    return _render_split_transaction_page_with_errors(request, original_transaction, formset)

def _render_split_transaction_page_with_errors(request, original_transaction, formset):
    all_categories_data = []
    all_subcategories_data = []

    current_year = date.today().year
    current_month = date.today().month
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            period_type='M', 
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            status='OU' 
        ).values_list('category__id', flat=True)
    )

    for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
        is_budgeted_for_display = cat.is_budgeted 
        is_fund_managed_for_display = cat.is_fund_managed
        is_goal_linked_for_display = cat.id in goal_linked_category_ids

        all_categories_data.append({ # Passe l'info des catégories
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': is_fund_managed_for_display,
            'is_budgeted': is_budgeted_for_display,
            'is_goal_linked': is_goal_linked_for_display
        })
        for child_cat in cat.children.all().order_by('name'):
            child_is_budgeted_for_display = child_cat.is_budgeted # Vérifie si la sous-catégorie est budgétée pour le mois en cours
            child_is_fund_managed_for_display = child_cat.is_fund_managed
            child_is_goal_linked_for_display = child_cat.id in goal_linked_category_ids # Vérifie si la sous-catégorie est liée à un objectif

            all_subcategories_data.append({
                'id': child_cat.id,
                'name': child_cat.name,
                'parent': cat.id,
                'is_fund_managed': child_is_fund_managed_for_display, # Passe l'info is_fund_managed
                'is_budgeted': child_is_budgeted_for_display,
                'is_goal_linked': child_is_goal_linked_for_display # Passe l'info is_goal_linked
            })

    context = {
        'page_title': 'Diviser une Transaction',
        'original_transaction': original_transaction, # Transaction originale à diviser
        'formset': formset,  # Formset pour la division de transaction
        'all_categories_data_json': json.dumps(all_categories_data), 
        'all_subcategories_data_json': json.dumps(all_subcategories_data), 
    }
    return render(request, 'webapp/split_transaction.html', context)
