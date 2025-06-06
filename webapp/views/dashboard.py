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

    # Filtrer uniquement les catégories parentes (sans parent) pour le premier dropdown
    categories = Category.objects.filter(parent__isnull=True).order_by('name')
    
    current_year = date.today().year
    current_month = date.today().month
    # IDs des catégories budgétées pour le mois et l'année en cours
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            period_type='M', 
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    # NOUVEAU: Préparez un ensemble des IDs de catégories liées à des objectifs d'épargne
    # Nous vérifions les objectifs "ouverts" car ce sont les objectifs actifs
    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            status='OU' 
        ).values_list('category__id', flat=True)
    )

    # Parcourir les catégories principales et leurs enfants pour préparer les données JSON
    for cat in categories:
        # Vérifier si la catégorie (ou l'une de ses sous-catégories si le flag est hérité) est budgétée,
        # gère un fonds, ou est liée à un objectif.
        # Note: Pour `is_budgeted` et `is_fund_managed`, nous utilisons les champs du modèle Category.
        # Pour `is_goal_linked`, nous vérifions si l'ID de la catégorie est dans l'ensemble des IDs liés aux objectifs.
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
        # Récupérer les sous-catégories pour le dropdown secondaire
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
    
    # Convertir les listes Python en chaînes JSON pour les passer au frontend
    all_categories_data_json = json.dumps(all_categories_data) 
    all_subcategories_data_json = json.dumps(all_subcategories_data) 

    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances, 
        'transactions': latest_transactions, 
        'form': form, 
        'all_categories_data_json': all_categories_data_json,  
        'all_subcategories_data_json': all_subcategories_data_json,  
    }
    return render(request, 'webapp/index.html', context)
