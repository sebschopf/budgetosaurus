# webapp/views/exports.py
import csv
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from webapp.models import Transaction

@login_required
def export_transactions_csv(request):
    """
    Vue pour exporter toutes les transactions de l'utilisateur connecté au format CSV.
    """
    # Créer la réponse HTTP avec le type de contenu CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="transactions_export.csv"'
    
    # Créer l'objet writer CSV
    writer = csv.writer(response)
    
    # Écrire l'en-tête
    writer.writerow([
        'Date',
        'Description',
        'Montant',
        'Devise',
        'Compte',
        'Type de Compte',
        'Catégorie',
        'Type de Transaction',
        'Créé le',
        'Modifié le'
    ])
    
    # Récupérer toutes les transactions de l'utilisateur
    transactions = Transaction.objects.filter(user=request.user).select_related(
        'account', 'category'
    ).order_by('-date', '-created_at')
    
    # Écrire les données des transactions
    for transaction in transactions:
        writer.writerow([
            transaction.date.strftime('%Y-%m-%d'),
            transaction.description,
            str(transaction.amount),
            transaction.account.currency,
            transaction.account.name,
            transaction.account.get_account_type_display(),
            transaction.category.name if transaction.category else 'Non catégorisé',
            transaction.get_transaction_type_display(),
            transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response
