# webapp/views/budgets.py
from datetime import date
import calendar
from django.shortcuts import render
from django.db.models import Sum

from ..models import Budget, Transaction, Fund # Importez le modèle Fund

def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours.
    Maintenant, elle affiche également les soldes des fonds budgétaires.
    """
    current_month = date.today().month
    current_year = date.today().year

    # Récupérer les budgets mensuels configurés pour le mois et l'année en cours (pour la planification)
    budgets = Budget.objects.filter(
        period_type='M',
        start_date__month=current_month,
        start_date__year=current_year
    ).select_related('category')

    budget_data = []
    for budget in budgets:
        # Calculer les dépenses réelles pour cette catégorie et ses sous-catégories pour le mois
        category_and_children_ids = [budget.category.id] + list(budget.category.children.values_list('id', flat=True))
        
        spent_amount = Transaction.objects.filter(
            category__id__in=category_and_children_ids,
            transaction_type='OUT',
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        spent_amount = abs(spent_amount)

        remaining = budget.amount - spent_amount
        percentage_spent = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0

        budget_data.append({
            'category_name': budget.category.name,
            'budgeted_amount': budget.amount,
            'spent_amount': spent_amount,
            'remaining': remaining,
            'percentage_spent': round(percentage_spent, 2),
            'status': 'ok' if remaining >= 0 else 'overbudget'
        })
    
    #  Récupérer les soldes des fonds budgétaires ---
    funds = Fund.objects.select_related('category').all().order_by('category__name')
    fund_data = []
    for fund in funds:
        fund_data.append({
            'category_name': fund.category.name,
            'current_balance': fund.current_balance,
        })


    total_income_month = Transaction.objects.filter(
        transaction_type='IN',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_expense_month = Transaction.objects.filter(
        transaction_type='OUT',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense_month = abs(total_expense_month)

    context = {
        'page_title': 'Aperçu des Budgets et Fonds', # Titre mis à jour
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'budget_data': budget_data, # Conserve les données de budget existantes pour comparaison
        'fund_data': fund_data, # données de fonds
        'total_income_month': total_income_month,
        'total_expense_month': total_expense_month,
    }
    return render(request, 'webapp/budget_overview.html', context)
