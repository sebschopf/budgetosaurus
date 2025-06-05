# webapp/views/budgets.py
from datetime import date
import calendar
from django.shortcuts import render
from django.db.models import Sum, F

from ..models import Budget, Transaction, Fund, Category

def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours.
    Maintenant, elle affiche également les soldes des fonds budgétaires et un récapitulatif mensuel par catégorie.
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
    
    #  Récupérer les soldes des fonds budgétaires (solde cumulatif des enveloppes) ---
    funds = Fund.objects.select_related('category').all().order_by('category__name')
    fund_data = []
    for fund in funds:
        fund_data.append({
            'category_name': fund.category.name,
            'current_balance': fund.current_balance,
            # Ajoute un 'status' pour la coloration : 'healthy' (sain), 'low' (faible), 'critical' (critique)
            'status': 'healthy' if fund.current_balance > 100 else ('low' if fund.current_balance > 0 else 'critical')
        })

    # --- NOUVEAU: Calcul du récapitulatif mensuel par catégorie (dépenses et revenus du mois) ---
    # Cela permet de voir le total des mouvements (IN/OUT) pour chaque catégorie pour le mois sélectionné,
    # sans lien avec le solde cumulatif des "Fonds".
    all_categories = Category.objects.filter(parent__isnull=True).order_by('name') # On agrège par catégories principales
    monthly_category_summary_data = []

    for main_cat in all_categories:
        # Inclure la catégorie principale et toutes ses sous-catégories pour le calcul du total
        category_ids_for_summary = [main_cat.id] + list(main_cat.children.values_list('id', flat=True))

        # Calculer le total des transactions (dépenses et revenus) pour cette catégorie
        # pour le mois et l'année en cours. F('amount') assure que les montants négatifs
        # (dépenses) et positifs (revenus) sont correctement additionnés.
        total_for_category = Transaction.objects.filter(
            category__id__in=category_ids_for_summary,
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # N'ajouter que les catégories qui ont eu des transactions ce mois-ci
        if total_for_category != 0:
            monthly_category_summary_data.append({
                'category_name': main_cat.name,
                'total_amount': total_for_category,
                # 'type' est utilisé pour l'affichage CSS (couleur positive/négative)
                'type': 'expense' if total_for_category < 0 else 'income' 
            })
    # Optionnel: trier par nom de catégorie pour un affichage cohérent
    monthly_category_summary_data.sort(key=lambda x: x['category_name'])


    # Calculs existants pour le résumé du mois (revenus/dépenses totaux)
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
    total_expense_month = abs(total_expense_month) # Absolu pour l'affichage

    context = {
        'page_title': 'Aperçu du Budget et Suivi', # Titre mis à jour pour la page globale
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'budget_data': budget_data, # Données pour les budgets planifiés vs réels
        'fund_data': fund_data, # Données pour les soldes des fonds (enveloppes cumulatives)
        'monthly_category_summary_data': monthly_category_summary_data, # NOUVEAU: récapitulatif mensuel par catégorie
        'total_income_month': total_income_month,
        'total_expense_month': total_expense_month,
    }
    return render(request, 'webapp/budget_overview.html', context)
