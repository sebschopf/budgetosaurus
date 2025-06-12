# webapp/views/general_transactions.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db.models import F, Sum
import json

from datetime import date
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone
import csv
from django.utils.translation import gettext as _

from webapp.models import Category, Transaction, Account, Budget, SavingGoal, Tag
from webapp.forms import TransactionForm
from webapp.services import TransactionService

@login_required
def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    Utilise TransactionService pour la logique métier, filtré par l'utilisateur connecté.
    """
    transaction_service = TransactionService()

    # Récupérer les comptes avec leurs soldes calculés
    accounts = Account.objects.filter(user=request.user).order_by('name')
    
    # Calculer le solde pour chaque compte
    for account in accounts:
        total_balance_change = account.transactions.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
        account.balance = account.initial_balance + total_balance_change

    latest_transactions = transaction_service.get_latest_transactions(request.user, limit=10)

    # Calcul des totaux pour l'aperçu rapide
    current_month = date.today().month
    current_year = date.today().year

    # Solde total de tous les comptes de l'utilisateur
    total_balance_change = Transaction.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    total_initial_balance = Account.objects.filter(user=request.user).aggregate(Sum('initial_balance'))['initial_balance__sum'] or 0
    total_balance = total_initial_balance + total_balance_change
    
    # Récupérer la devise de base pour l'affichage
    base_currency = accounts.first().currency if accounts.exists() else 'CHF'

    # Revenu du mois courant
    monthly_income = Transaction.objects.filter(
        user=request.user,
        transaction_type='IN',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    # Dépenses du mois courant (en valeur absolue)
    monthly_expense = Transaction.objects.filter(
        user=request.user,
        transaction_type='OUT',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expense = abs(monthly_expense)

    # Préparation des données pour les catégories et sous-catégories (pour Alpine.js)
    form = TransactionForm(user=request.user)

    all_categories_data = []
    all_subcategories_data = []

    categories = Category.objects.filter(user=request.user, parent__isnull=True).order_by('name')

    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            user=request.user,
            period_type='M',
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            user=request.user,
            status='OU'
        ).values_list('category__id', flat=True)
    )

    for cat in categories:
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
        for child_cat in cat.children.filter(user=request.user).order_by('name'):
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

    all_categories_data_json = json.dumps(all_categories_data)
    all_subcategories_data_json = json.dumps(all_subcategories_data)

    # Récupérer tous les tags disponibles pour l'utilisateur
    available_tags = Tag.objects.filter(user=request.user).order_by('name')

    context = {
        'page_title': 'Tableau de Bord',
        'accounts': accounts,  # Objets Account avec balance calculée
        'latest_transactions': latest_transactions,
        'form': form,
        'all_categories_data_json': all_categories_data_json,
        'all_subcategories_data_json': all_subcategories_data_json,
        'available_tags': available_tags,  # Pour les checkboxes des tags
        'total_balance': total_balance,
        'base_currency': base_currency,
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
    }
    return render(request, 'webapp/index.html', context)


@login_required
@require_POST
def add_transaction_submit(request):
    """
    Traite la soumission du formulaire d'ajout de transaction via AJAX.
    Utilise TransactionService pour la logique métier.
    """
    transaction_service = TransactionService()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        form = TransactionForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                cleaned_data = form.cleaned_data
                tags_list = list(cleaned_data.pop('tags'))
                
                # Récupérer la catégorie finale (sous-catégorie ou catégorie principale)
                final_category = cleaned_data.pop('final_category', None)
                
                transaction_data = {
                    'date': cleaned_data['date'],
                    'description': cleaned_data['description'],
                    'amount': cleaned_data['amount'],
                    'category': final_category,
                    'account': cleaned_data['account'],
                    'transaction_type': cleaned_data['transaction_type'],
                    'tags': tags_list,
                }
                
                # Créer la transaction avec l'utilisateur
                transaction = transaction_service.create_transaction(transaction_data, request.user)
                
                return JsonResponse({
                    'success': True,
                    'message': f"Transaction '{transaction.description}' ajoutée avec succès."
                })
                
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f"Erreur lors de l'ajout de la transaction: {str(e)}"
                })
        else:
            # Retourner les erreurs du formulaire
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'message': "Veuillez corriger les erreurs dans le formulaire.",
                'errors': errors
            })
    
    # Si ce n'est pas une requête AJAX, rediriger vers le dashboard
    return redirect('dashboard_view')


@login_required
def split_transaction_view(request, transaction_id):
    """
    Vue pour diviser une transaction en plusieurs transactions.
    """
    # S'assurer que la transaction appartient à l'utilisateur connecté
    original_transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
    
    # Récupérer toutes les catégories pour cet utilisateur
    all_categories = Category.objects.filter(user=request.user, parent__isnull=True).order_by('name')
    all_subcategories = Category.objects.filter(user=request.user, parent__isnull=False).order_by('name')
    
    all_categories_json = json.dumps([
        {
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed,
            'is_budgeted': cat.is_budgeted
        }
        for cat in all_categories
    ])
    
    all_subcategories_json = json.dumps([
        {
            'id': cat.id,
            'name': cat.name,
            'parent': cat.parent.id,
            'is_fund_managed': cat.is_fund_managed,
            'is_budgeted': cat.is_budgeted
        }
        for cat in all_subcategories
    ])
    
    if request.method == 'POST':
        # Traitement du formulaire de division
        messages.success(request, "Transaction divisée avec succès.")
        return redirect('dashboard_view')
    
    context = {
        'original_transaction': original_transaction,
        'all_categories_json': all_categories_json,
        'all_subcategories_json': all_subcategories_json,
    }
    
    return render(request, 'webapp/split_transaction.html', context)
