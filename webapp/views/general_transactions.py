# webapp/views/general_transactions.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db.models import F
import json
from datetime import date
from django.contrib.auth.decorators import login_required # NOUVEAU: Importez le décorateur

from webapp.models import Category, Transaction, Account, Budget, SavingGoal
from webapp.forms import TransactionForm
from webapp.services import TransactionService

@login_required # NOUVEAU: Protégez cette vue pour les utilisateurs connectés
def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    Utilise TransactionService pour la logique métier, filtré par l'utilisateur connecté.
    """
    transaction_service = TransactionService() # NOUVEAU: Plus besoin de passer des arguments à l'initialisation

    # NOUVEAU: Passez request.user aux méthodes de service
    account_balances = transaction_service.get_account_balances(request.user)
    latest_transactions = transaction_service.get_latest_transactions(request.user, limit=10)

    form = TransactionForm(user=request.user) # NOUVEAU: Passez l'utilisateur au formulaire

    all_categories_data = []
    all_subcategories_data = []

    # NOUVEAU: Filtrer les catégories par l'utilisateur connecté
    categories = Category.objects.filter(user=request.user, parent__isnull=True).order_by('name')

    current_year = date.today().year
    current_month = date.today().month
    # NOUVEAU: Filtrer les budgets et objectifs d'épargne par l'utilisateur
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            user=request.user, # NOUVEAU
            period_type='M',
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            user=request.user, # NOUVEAU
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
        # S'assurer que les sous-catégories sont aussi filtrées par l'utilisateur
        for child_cat in cat.children.filter(user=request.user).order_by('name'): # NOUVEAU
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

    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances,
        'transactions': latest_transactions,
        'form': form,
        'all_categories_data_json': all_categories_data_json,
        'all_subcategories_data_json': all_subcategories_data_json,
    }
    return render(request, 'webapp/index.html', context)


@login_required # Protégez cette vue
@require_POST
def add_transaction_submit(request):
    """
    Gère la soumission du formulaire d'ajout de transaction depuis le tableau de bord.
    Utilise TransactionService pour la création pour l'utilisateur connecté.
    """
    # Passez l'utilisateur au formulaire pour qu'il filtre les choix
    form = TransactionForm(request.POST, user=request.user)
    transaction_service = TransactionService()

    if form.is_valid():
        try:
            cleaned_data = form.cleaned_data
            tags_list = list(cleaned_data.pop('tags'))

            final_category = cleaned_data.pop('final_category')

            transaction_data = {
                'date': cleaned_data['date'],
                'description': cleaned_data['description'],
                'amount': cleaned_data['amount'],
                'category': final_category,
                'account': cleaned_data['account'],
                'transaction_type': cleaned_data['transaction_type'],
                'tags': tags_list,
            }

            # NOUVEAU: Passez request.user à la méthode create_transaction
            transaction_service.create_transaction(transaction_data, request.user)
            messages.success(request, "Transaction enregistrée avec succès!")
            return redirect('dashboard_view')
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement de la transaction: {e}")

    # Re-rendre la page si le formulaire est invalide
    all_categories_data = []
    all_subcategories_data = []

    current_year = date.today().year
    current_month = date.today().month
    # Filtrer les budgets et objectifs d'épargne par l'utilisateur
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            user=request.user, # NOUVEAU
            period_type='M',
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )
    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            user=request.user, # NOUVEAU
            status='OU'
        ).values_list('category__id', flat=True)
    )

    # Filtrer les catégories par l'utilisateur connecté
    for cat in Category.objects.filter(user=request.user, parent__isnull=True).order_by('name'):
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
        # S'assurer que les sous-catégories sont aussi filtrées par l'utilisateur
        for child_cat in cat.children.filter(user=request.user).order_by('name'): # NOUVEAU
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
        'page_title': 'Tableau de Bord',
        # Passez request.user aux méthodes de service pour le re-rendu
        'account_balances': transaction_service.get_account_balances(request.user),
        'transactions': transaction_service.get_latest_transactions(request.user, limit=10),
        'form': form,
        'all_categories_data_json': json.dumps(all_categories_data),
        'all_subcategories_data_json': json.dumps(all_subcategories_data),
    }
    return render(request, 'webapp/index.html', context)


@login_required # Protégez cette vue
@require_GET
def load_subcategories(request):
    """
    Vue AJAX pour charger les sous-catégories en fonction d'une catégorie parente sélectionnée,
    incluant le statut is_fund_managed, is_budgeted et is_goal_linked, pour l'utilisateur connecté.
    """
    parent_id = request.GET.get('parent_category_id')
    subcategories = []
    if parent_id:
        try:
            # Filtrer par l'utilisateur
            parent_category = Category.objects.get(pk=parent_id, user=request.user)
            # Filtrer les enfants par l'utilisateur
            children = parent_category.children.filter(user=request.user).order_by('name')

            # Ajoutez les imports nécessaires pour Budget et SavingGoal (si non déjà importés globalement dans la vue)
            # Ils sont déjà importés en haut du fichier, donc pas besoin ici.

            current_year = date.today().year
            current_month = date.today().month
            # Filtrer les objectifs d'épargne par l'utilisateur
            goal_linked_category_ids = set(
                SavingGoal.objects.filter(user=request.user, status='OU').values_list('category__id', flat=True)
            )

            for child in children:
                is_budgeted_for_display = child.is_budgeted
                is_fund_managed_for_display = child.is_fund_managed
                is_goal_linked_for_display = child.id in goal_linked_category_ids

                subcategories.append({
                    'id': child.id,
                    'name': child.name,
                    'is_fund_managed': is_fund_managed_for_display,
                    'is_budgeted': is_budgeted_for_display,
                    'is_goal_linked': is_goal_linked_for_display
                })
        except Category.DoesNotExist:
            pass # Si la catégorie parente n'existe pas ou n'appartient pas à l'utilisateur
    return JsonResponse(subcategories, safe=False)


@login_required # Protégez cette vue
@require_GET
def get_common_descriptions(request):
    """
    Vue AJAX pour récupérer les descriptions de transactions les plus courantes pour l'utilisateur connecté.
    """
    # Filtrer les transactions par l'utilisateur
    common_descriptions = Transaction.objects.filter(
        user=request.user, # NOUVEAU
        description__isnull=False
    ).exclude(
        description__exact=''
    ).values(
        'description'
    ).annotate(
        count=F('description')
    ).order_by(
        '-count'
    ).values_list(
        'description', flat=True
    ).distinct()[:10]

    return JsonResponse(list(common_descriptions), safe=False)
