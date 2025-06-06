# webapp/views/summary_views.py
from django.shortcuts import render
from django.db.models import F
import calendar
from datetime import date

from webapp.models import Transaction, Category # Importez les modèles nécessaires

def recap_overview_view(request):
    """
    Vue pour la page d'aperçu des différents récapitulatifs et outils de gestion.
    Sert de hub pour les vues de transactions détaillées et de division.
    """
    context = {
        'page_title': 'Vos Récapitulatifs et Outils',
    }
    return render(request, 'webapp/recap_overview.html', context)


def category_transactions_summary_view(request, year=None, month=None):
    """
    Vue affichant un récapitulatif des transactions,
    regroupées par catégories qui sont désignées comme "gérant un fonds" (`is_fund_managed`).
    Affiche les transactions individuelles pour chaque catégorie pour la période spécifiée.
    """
    today = date.today()
    
    # Déterminer l'année et le mois à filtrer
    if year is None:
        selected_year = today.year
    else:
        selected_year = int(year)
        
    selected_month = None # Initialiser à None pour le cas "année courante"

    if month is None:
        # Si le mois n'est pas spécifié, on est en mode "année courante"
        period_type = 'year'
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31) 
        period_display = f"Année {selected_year}"
    else:
        # Si le mois est spécifié, on est en mode "mois courant"
        period_type = 'month'
        selected_month = int(month)
        start_date = date(selected_year, selected_month, 1)
        _, last_day = calendar.monthrange(selected_year, selected_month)
        end_date = date(selected_year, selected_month, last_day)
        period_display = f"{calendar.month_name[selected_month]} {selected_year}"


    # Récupérer uniquement les catégories marquées comme gérant un fonds
    fund_managed_categories = Category.objects.filter(is_fund_managed=True).order_by('name')

    category_transactions_summary = []

    for category in fund_managed_categories:
        # Obtenir les IDs de la catégorie et de ses enfants
        category_ids_for_query = [category.id] + list(category.children.values_list('id', flat=True))

        # Filtrer les transactions pour la période donnée
        transactions_in_category = Transaction.objects.filter(
            category__id__in=category_ids_for_query,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('date', 'created_at')

        if transactions_in_category.exists():
            transaction_list_data = []
            for transaction in transactions_in_category:
                transaction_list_data.append({
                    'date': transaction.date,
                    'description': transaction.description,
                    'amount': transaction.amount,
                    'transaction_type': transaction.get_transaction_type_display(),
                    'account_name': transaction.account.name,
                    'account_currency': transaction.account.currency,
                })
            
            category_transactions_summary.append({
                'category_name': category.name,
                'transactions': transaction_list_data
            })
    
    context = {
        'page_title': 'Récapitulatif des Transactions par Catégorie',
        'current_period_display': period_display,
        'category_transactions_summary': category_transactions_summary,
        'today_year': today.year,
        'today_month': today.month,
        'selected_year': selected_year,
        'selected_month': selected_month,
    }
    return render(request, 'webapp/category_transactions_summary.html', context)


def all_transactions_summary_view(request):
    """
    Vue affichant un récapitulatif de toutes les transactions,
    avec une indication si elles ont été ventilées (ont une allocation).
    """
    # Utilise prefetch_related pour charger les allocations et les débits de fonds en une seule requête,
    # car ce sont des OneToOneField inversées.
    all_transactions = Transaction.objects.select_related('category', 'account').prefetch_related('allocation', 'fund_debit_record').order_by('-date', '-created_at')

    transactions_data = []
    for transaction in all_transactions:
        # Vérifier si la transaction a une allocation associée
        is_allocated = hasattr(transaction, 'allocation') and transaction.allocation is not None
        # Vérifier si la transaction a un enregistrement de débit de fonds associé
        is_fund_debited = hasattr(transaction, 'fund_debit_record') and transaction.fund_debit_record is not None


        transactions_data.append({
            'id': transaction.id,
            'date': transaction.date,
            'description': transaction.description,
            'amount': transaction.amount,
            'category_name': transaction.category.name if transaction.category else 'N/A',
            'account_name': transaction.account.name,
            'account_currency': transaction.account.currency,
            'transaction_type': transaction.transaction_type, # MODIFIÉ: Utilise la valeur interne ('IN', 'OUT', 'TRF')
            'is_allocated': is_allocated,
            'is_fund_debited': is_fund_debited,
            'account_type': transaction.account.account_type,
        })
    
    context = {
        'page_title': 'Toutes les Transactions',
        'transactions': transactions_data,
    }
    return render(request, 'webapp/all_transactions_summary.html', context)
