# webapp/views/dashboard.py
from django.shortcuts import render
import json 
from datetime import date 

from ..services import TransactionService
from ..models import Category, Budget, SavingGoal # NOUVEAU: Importez SavingGoal

def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    Utilise TransactionService pour la logique métier.
    """
    transaction_service = TransactionService() 

    account_balances = transaction_service.get_account_balances()
    latest_transactions = transaction_service.get_latest_transactions(limit=10)

    from ..forms import TransactionForm
    form = TransactionForm()

    all_categories_data = []
    all_subcategories_data = []

    categories = Category.objects.filter(parent__isnull=True).order_by('name')
    
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

    for cat in categories:
        is_budgeted_for_display = cat.is_budgeted # Vérifie si la catégorie est budgétée pour le mois en cours
        is_fund_managed_for_display = cat.is_fund_managed # Vérifie si la catégorie gère un fonds
        is_goal_linked_for_display = cat.id in goal_linked_category_ids # Vérifie si la catégorie est liée à un objectif

        all_categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': is_fund_managed_for_display, # Passe l'info is_fund_managed
            'is_budgeted': is_budgeted_for_display, # Vérifie si la catégorie est budgétée
            'is_goal_linked': is_goal_linked_for_display # Passe l'info is_goal_linked
        })
        for child_cat in cat.children.all().order_by('name'): # Récupère les sous-catégories
            child_is_budgeted_for_display = child_cat.is_budgeted # Vérifie si la sous-catégorie est budgétée pour le mois en cours
            child_is_fund_managed_for_display = child_cat.is_fund_managed # Vérifie si la sous-catégorie gère un fonds
            child_is_goal_linked_for_display = child_cat.id in goal_linked_category_ids # Vérifie si la sous-catégorie est liée à un objectif

            all_subcategories_data.append({
                'id': child_cat.id,
                'name': child_cat.name,
                'parent': cat.id,
                'is_fund_managed': child_is_fund_managed_for_display, # Passe l'info is_fund_managed
                'is_budgeted': child_is_budgeted_for_display, # Vérifie si la sous-catégorie est budgétée
                'is_goal_linked': child_is_goal_linked_for_display # Passe l'info is_goal_linked
            })
    
    all_categories_data_json = json.dumps(all_categories_data) # Pour la modale d'édition
    all_subcategories_data_json = json.dumps(all_subcategories_data) # Pour la modale d'édition

    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances, # Récupère les soldes des comptes
        'transactions': latest_transactions, # Récupère les dernières transactions
        'form': form,  # Formulaire pour ajouter une transaction
        'all_categories_data_json': all_categories_data_json,  # Pour la modale d'édition
        'all_subcategories_data_json': all_subcategories_data_json,  # Pour la modale d'édition
    }
    return render(request, 'webapp/index.html', context)
