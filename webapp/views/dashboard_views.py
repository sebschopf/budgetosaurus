# webapp/views/dashboard_views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from datetime import date
from django.db.models import Sum
from webapp.models import Transaction, Category

@login_required
def dashboard_view(request):
    """
    Vue principale du tableau de bord avec Alpine.js
    CORRECTION: Ne plus filtrer par mois courant
    """
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # Statistiques rapides pour l'utilisateur connecté
    total_transactions = Transaction.objects.filter(user=request.user).count()
    
    # CORRECTION: Prendre TOUTES les transactions de l'année en cours
    yearly_transactions = Transaction.objects.filter(
        user=request.user,
        date__year=current_year
    )
    
    # Si pas de transactions cette année, prendre toutes les transactions
    if not yearly_transactions.exists():
        yearly_transactions = Transaction.objects.filter(user=request.user)
        period_name = "Total"
    else:
        period_name = f"{current_year}"
    
    yearly_income = yearly_transactions.filter(amount__gt=0).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    yearly_expenses = yearly_transactions.filter(amount__lt=0).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Transactions non catégorisées
    uncategorized_count = Transaction.objects.filter(
        user=request.user,
        category__isnull=True
    ).count()
    
    context = {
        'page_title': 'Tableau de Bord',
        'total_transactions': total_transactions,
        'monthly_income': yearly_income,
        'monthly_expenses': abs(yearly_expenses),
        'monthly_balance': yearly_income + yearly_expenses,
        'uncategorized_count': uncategorized_count,
        'current_month_name': period_name,
        'current_year': current_year,
    }
    
    return render(request, 'webapp/dashboard.html', context)

@login_required
def budget_overview(request):
    """
    Vue pour l'aperçu des budgets avec données réelles
    CORRECTION: Supprimer les budgets hardcodés à 500 CHF
    """
    today = date.today()
    current_month = today.month
    current_year = today.year
    
    # CORRECTION: Prendre toutes les transactions de l'année
    yearly_transactions = Transaction.objects.filter(
        user=request.user,
        date__year=current_year
    )
    
    # Si pas de transactions cette année, prendre toutes
    if not yearly_transactions.exists():
        yearly_transactions = Transaction.objects.filter(user=request.user)
    
    # Calculs pour le résumé annuel
    total_income_year = yearly_transactions.filter(amount__gt=0).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    total_expense_year = yearly_transactions.filter(amount__lt=0).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Données pour les fonds budgétaires (catégories gérées par fonds)
    fund_managed_categories = Category.objects.filter(
        user=request.user, 
        is_fund_managed=True
    ).order_by('name')
    
    fund_data = []
    for category in fund_managed_categories:
        # Calculer le solde actuel pour cette catégorie
        category_transactions = Transaction.objects.filter(
            user=request.user,
            category=category
        )
        
        current_balance = category_transactions.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Déterminer le statut du fonds
        if current_balance >= 100:  # Seuil arbitraire pour "sain"
            status = 'healthy'
        elif current_balance >= 0:
            status = 'low'
        else:
            status = 'critical'
        
        fund_data.append({
            'category_name': category.name,
            'current_balance': current_balance,
            'status': status
        })
    
    # CORRECTION: Supprimer les budgets hardcodés
    # Données pour les budgets de planification (catégories budgétées)
    from webapp.models import Budget
    
    budgeted_categories = Category.objects.filter(
        user=request.user, 
        is_budgeted=True
    ).order_by('name')

    budget_data = []
    for category in budgeted_categories:
        # Chercher un budget réel pour cette catégorie
        budget = Budget.objects.filter(
            user=request.user,
            category=category,
            start_date__lte=today,
            end_date__gte=today
        ).first()
        
        if budget:
            # Montant dépensé dans cette catégorie
            spent_amount = yearly_transactions.filter(
                category=category,
                amount__lt=0
            ).aggregate(total=Sum('amount'))['total'] or 0
            spent_amount = abs(spent_amount)
            
            budgeted_amount = budget.amount
            remaining = budgeted_amount - spent_amount
            percentage_spent = float(spent_amount / budgeted_amount * 100) if budgeted_amount > 0 else 0
            
            budget_data.append({
                'category_name': category.name,
                'budgeted_amount': budgeted_amount,
                'spent_amount': spent_amount,
                'remaining': remaining,
                'percentage_spent': percentage_spent
            })
    
    # Récapitulatif annuel par catégorie
    monthly_category_summary_data = []
    categories_with_transactions = Category.objects.filter(
        user=request.user,
        transactions__date__year=current_year
    ).distinct()
    
    for category in categories_with_transactions:
        total_amount = yearly_transactions.filter(
            category=category
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        monthly_category_summary_data.append({
            'category_name': category.name,
            'total_amount': total_amount
        })
    
    context = {
        'page_title': 'Aperçu des Budgets',
        'total_income_month': total_income_year,
        'total_expense_month': total_expense_year,
        'fund_data': fund_data,
        'budget_data': budget_data,
        'monthly_category_summary_data': monthly_category_summary_data,
    }
    
    return render(request, 'webapp/budget_overview.html', context)

@login_required
def glossary_view(request):
    """
    Vue pour le glossaire
    """
    context = {
        'page_title': 'Glossaire',
    }
    return render(request, 'webapp/glossary.html', context)
