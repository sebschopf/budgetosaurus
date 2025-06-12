# webapp/views/summary_views.py
from django.shortcuts import render, redirect
from django.db.models import Sum
import calendar
import json
from datetime import date
from django.contrib.auth.decorators import login_required 

from webapp.models import Transaction, Category
from webapp.services.permission_service import PermissionService

@login_required
def recap_overview_view(request):
    """
    Vue pour la page d'aperçu des différents récapitulatifs et outils de gestion.
    """
    context = {
        'page_title': 'Vos Récapitulatifs et Outils',
    }
    return render(request, 'webapp/recap_overview.html', context)

@login_required 
def category_transactions_summary_view(request, year=None, month=None):
    """
    Vue affichant un récapitulatif des transactions par catégories.
    CORRECTION: Afficher les transactions même sans catégories de fonds
    """
    today = date.today()

    # Récupérer TOUTES les transactions de l'utilisateur
    accessible_transactions = Transaction.objects.filter(user=request.user)
    accessible_categories = Category.objects.filter(user=request.user)

    # Si aucune année spécifiée, prendre l'année avec le plus de données
    if year is None:
        latest_transaction = accessible_transactions.order_by('-date').first()
        if latest_transaction:
            selected_year = latest_transaction.date.year
        else:
            selected_year = today.year
    else:
        selected_year = int(year)

    # Validation du mois
    if month is not None:
        try:
            selected_month = int(month)
            if selected_month < 1 or selected_month > 12:
                return redirect('category_transactions_summary_view', year=selected_year)
        except (ValueError, TypeError):
            return redirect('category_transactions_summary_view', year=selected_year)
    else:
        selected_month = None

    if month is None:
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)
        period_display = f"Année {selected_year}"
    else:
        start_date = date(selected_year, selected_month, 1)
        _, last_day = calendar.monthrange(selected_year, selected_month)
        end_date = date(selected_year, selected_month, last_day)
        month_name = calendar.month_name[selected_month]
        period_display = f"{month_name} {selected_year}"

    # CORRECTION: Afficher TOUTES les catégories avec transactions, pas seulement celles gérées par fonds
    categories_with_transactions = accessible_categories.filter(
        transactions__date__gte=start_date,
        transactions__date__lte=end_date,
        transactions__user=request.user
    ).distinct().order_by('name')

    category_transactions_summary = []

    for category in categories_with_transactions:
        # Filtrer les transactions pour la période donnée
        transactions_in_category = accessible_transactions.filter(
            category=category,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'created_at')

        if transactions_in_category.exists():
            transaction_list_data = []
            for transaction in transactions_in_category:
                transaction_list_data.append({
                    'id': transaction.id,
                    'date': transaction.date.isoformat(),
                    'description': transaction.description,
                    'amount': float(transaction.amount),
                    'transaction_type': transaction.get_transaction_type_display(),
                    'account_name': transaction.account.name,
                    'account_currency': transaction.account.currency,
                    'owner': transaction.user.username,
                })

            category_transactions_summary.append({
                'category_name': category.name,
                'transactions': transaction_list_data
            })

    # Convertir en JSON pour Alpine.js
    category_transactions_summary_json = json.dumps(category_transactions_summary)

    # Récupérer toutes les années disponibles
    available_years = accessible_transactions.dates('date', 'year')
    available_years = sorted([d.year for d in available_years], reverse=True)
    
    if not available_years:
        available_years = [today.year]

    context = {
        'page_title': 'Récapitulatif des Transactions par Catégorie',
        'current_period_display': period_display,
        'category_transactions_summary': category_transactions_summary_json,
        'today_year': today.year,
        'today_month': today.month,
        'selected_year': selected_year,
        'selected_month': selected_month,
        'available_years': available_years,
    }
    return render(request, 'webapp/category_transactions_summary.html', context)

@login_required
def all_transactions_summary_view(request):
    """
    Vue affichant toutes les transactions accessibles selon les permissions.
    CORRECTION: Simplifier pour afficher vraiment toutes les transactions
    """
    # DEBUG: Informations de diagnostic
    debug_info = {
        'current_user': request.user.username,
        'user_id': request.user.id,
        'is_superuser': request.user.is_superuser,
    }
    
    # CORRECTION: Récupérer directement les transactions de l'utilisateur
    all_transactions_query = Transaction.objects.filter(user=request.user)
    
    debug_info.update({
        'total_transactions_in_db': Transaction.objects.count(),
        'user_own_transactions': all_transactions_query.count(),
        'accessible_transactions_count': all_transactions_query.count(),
        'permission_bypass': "Accès direct aux transactions de l'utilisateur"
    })
    
    all_transactions = all_transactions_query.select_related('category', 'account').order_by('-date', '-created_at')

    transactions_data = []
    for transaction in all_transactions:
        transactions_data.append({
            'id': transaction.id,
            'date': transaction.date,
            'description': transaction.description,
            'amount': transaction.amount,
            'category_name': transaction.category.name if transaction.category else 'N/A',
            'account_name': transaction.account.name,
            'account_currency': transaction.account.currency,
            'transaction_type': transaction.transaction_type,
            'is_allocated': False,
            'is_fund_debited': False,
            'account_type': transaction.account.account_type,
            'owner': transaction.user.username,
            'can_edit': True,  # L'utilisateur peut toujours éditer ses propres transactions
        })

    context = {
        'page_title': 'Toutes les Transactions',
        'transactions': transactions_data,
        'debug_info': debug_info,
    }
    return render(request, 'webapp/all_transactions_summary.html', context)

@login_required
def review_transactions_view(request):
    """
    Vue affichant les transactions qui nécessitent une révision.
    CORRECTION MAJEURE: Récupération directe sans service de permissions
    """
    print(f"DEBUG: Utilisateur connecté: {request.user.username}")
    
    # CORRECTION: Récupération directe des transactions non catégorisées
    transactions_to_review = Transaction.objects.filter(
        user=request.user,
        category__isnull=True
    ).select_related('account').order_by('-date', '-created_at')
    
    print(f"DEBUG: Transactions trouvées: {transactions_to_review.count()}")
    
    # Créer le JSON des transactions de manière sécurisée
    transactions_data = []
    for transaction in transactions_to_review:
        transactions_data.append({
            'id': transaction.id,
            'date': transaction.date.strftime('%Y-%m-%d'),
            'description': transaction.description,
            'amount': float(transaction.amount),
            'account_name': transaction.account.name,
            'account_currency': transaction.account.currency,
        })
    
    # Convertir en JSON de manière sécurisée
    transactions_json = json.dumps(transactions_data, ensure_ascii=False)

    context = {
        'page_title': 'Transactions à Revoir',
        'transactions_to_review': transactions_to_review,
        'transactions_json': transactions_json,
    }
    return render(request, 'webapp/review_transactions.html', context)
