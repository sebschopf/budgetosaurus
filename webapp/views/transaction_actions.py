# webapp/views/transaction_actions.py
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json

from webapp.models import Transaction, Category # Importez les modèles nécessaires
from webapp.forms import TransactionForm # Importez le formulaire
from webapp.services import TransactionService # Importez le service

@require_POST
def delete_selected_transactions(request):
    """
    Vue pour supprimer les transactions sélectionnées par l'utilisateur.
    """
    transaction_ids = request.POST.getlist('transaction_ids')
    
    if not transaction_ids:
        messages.error(request, "Aucune transaction sélectionnée pour la suppression.")
        return redirect('dashboard_view') # Ou vers la page d'où vient la requête si possible

    try:
        with Transaction.objects.atomic(): # Utiliser transaction.atomic() directement depuis le modèle
            deleted_count, _ = Transaction.objects.filter(id__in=transaction_ids).delete()
        
        messages.success(request, f"{deleted_count} transaction(s) supprimée(s) avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression des transactions: {e}")
    
    return redirect('dashboard_view') # Rediriger vers le tableau de bord ou la page de révision


@require_GET
def get_transaction_form_for_edit(request, transaction_id):
    """
    Vue AJAX pour récupérer le formulaire d'édition d'une transaction spécifique.
    Le formulaire est pré-rempli avec les données de la transaction.
    """
    transaction = get_object_or_404(Transaction, pk=transaction_id)
    form = TransactionForm(instance=transaction)
    
    # Récupérer toutes les catégories pour le JS, incluant l'info is_fund_managed
    all_categories_data = []
    all_subcategories_data = []

    for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
        all_categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })
        for child_cat in cat.children.all().order_by('name'):
            all_subcategories_data.append({
                'id': child_cat.id,
                'name': child_cat.name,
                'parent': cat.id,
                'is_fund_managed': child_cat.is_fund_managed
            })

    context = {
        'form': form, 
        'transaction_id': transaction_id,
        'all_categories_data_json': json.dumps(all_categories_data), # Pour la modale d'édition
        'all_subcategories_data_json': json.dumps(all_subcategories_data), # Pour la modale d'édition
    }
    return render(request, 'webapp/dashboard_includes/edit_transaction_form_partial.html', context)


@require_GET
def suggest_transaction_categorization(request):
    """
    Vue AJAX pour suggérer une catégorie et des tags basés sur une description de transaction.
    Utilise le TransactionService pour la logique d'apprentissage.
    """
    description = request.GET.get('description', '')
    transaction_service = TransactionService()
    suggestion = transaction_service.suggest_categorization(description)
    return JsonResponse(suggestion)

