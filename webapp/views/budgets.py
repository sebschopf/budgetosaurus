# webapp/views/budgets.py
from datetime import date
import calendar
from django.shortcuts import render
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required

from ..models import Budget, Transaction, Fund, Category

@login_required
def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours
    pour l'utilisateur connecté.
    Maintenant, elle affiche également les soldes des fonds budgétaires et un récapitulatif mensuel par catégorie.
    """
    current_month = date.today().month
    current_year = date.today().year

    # Récupérer les budgets mensuels configurés pour le mois et l'année en cours POUR L'UTILISATEUR CONNECTÉ
    budgets = Budget.objects.filter(
        user=request.user,
        period_type='M',
        start_date__month=current_month,
        start_date__year=current_year
    ).select_related('category')

    budget_data = []
    for budget in budgets:
        # Calculer les dépenses réelles pour cette catégorie et ses sous-catégories pour le mois POUR L'UTILISATEUR CONNECTÉ
        category_and_children_ids = [budget.category.id] + list(budget.category.children.filter(user=request.user).values_list('id', flat=True)) # NOUVEAU

        spent_amount = Transaction.objects.filter(
            user=request.user,
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

    # Récupérer les soldes des fonds budgétaires POUR L'UTILISATEUR CONNECTÉ
    funds = Fund.objects.filter(user=request.user).select_related('category').all().order_by('category__name')
    fund_data = []
    for fund in funds:
        fund_data.append({
            'category_name': fund.category.name,
            'current_balance': fund.current_balance,
            'status': 'healthy' if fund.current_balance > 100 else ('low' if fund.current_balance > 0 else 'critical')
        })

    # Calcul du récapitulatif mensuel par catégorie (dépenses et revenus du mois) POUR L'UTILISATEUR CONNECTÉ
    all_categories = Category.objects.filter(user=request.user, parent__isnull=True).order_by('name')
    monthly_category_summary_data = []

    for main_cat in all_categories:
        # Inclure la catégorie principale et toutes ses sous-catégories POUR L'UTILISATEUR CONNECTÉ
        category_ids_for_summary = [main_cat.id] + list(main_cat.children.filter(user=request.user).values_list('id', flat=True)) # NOUVEAU

        # Calculer le total des transactions (dépenses et revenus) POUR L'UTILISATEUR CONNECTÉ
        total_for_category = Transaction.objects.filter(
            user=request.user,
            category__id__in=category_ids_for_summary,
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        if total_for_category != 0:
            monthly_category_summary_data.append({
                'category_name': main_cat.name,
                'total_amount': total_for_category,
                'type': 'expense' if total_for_category < 0 else 'income'
            })
    monthly_category_summary_data.sort(key=lambda x: x['category_name'])

    # Filtrer les revenus/dépenses totaux par l'utilisateur
    total_income_month = Transaction.objects.filter(
        user=request.user,
        transaction_type='IN',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_expense_month = Transaction.objects.filter(
        user=request.user,
        transaction_type='OUT',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense_month = abs(total_expense_month)

    context = {
        'page_title': 'Aperçu du Budget et Suivi',
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'budget_data': budget_data,
        'fund_data': fund_data,
        'monthly_category_summary_data': monthly_category_summary_data,
        'total_income_month': total_income_month,
        'total_expense_month': total_expense_month,
    }
    return render(request, 'webapp/budget_overview.html', context)
