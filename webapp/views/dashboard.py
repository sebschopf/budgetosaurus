# webapp/views/dashboard.py
from django.shortcuts import render
from ..services import TransactionService # Remonter d'un niveau pour importer services

def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    Utilise TransactionService pour la logique métier.
    """
    transaction_service = TransactionService() # Instanciation du service

    account_balances = transaction_service.get_account_balances()
    latest_transactions = transaction_service.get_latest_transactions(limit=10)

    # Préparer une instance du formulaire de transaction
    # Note: Le formulaire est importé dans la vue locale car il est directement lié à la présentation
    from ..forms import TransactionForm
    form = TransactionForm()

    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances,
        'transactions': latest_transactions,
        'form': form, # Le formulaire est inclus pour être affiché dans le template
    }
    return render(request, 'webapp/index.html', context)
