# webapp/views/transactions.py
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db.models import F
from django.db import transaction as db_transaction

from webapp.models import Category, Transaction, Account, Tag # Assurez-vous d'importer Tag
from webapp.forms import TransactionForm
from webapp.services import TransactionService


@require_POST
def add_transaction_submit(request):
    """
    Gère la soumission du formulaire d'ajout de transaction depuis le tableau de bord.
    Utilise TransactionService pour la création.
    """
    form = TransactionForm(request.POST)
    transaction_service = TransactionService()

    if form.is_valid():
        try:
            # Les données nettoyées du formulaire incluent maintenant 'tags' comme QuerySet d'objets Tag
            # Le service attend une liste d'objets Tag pour le champ 'tags'.
            cleaned_data = form.cleaned_data
            tags_list = list(cleaned_data.pop('tags')) # Convertir le QuerySet en liste

            transaction_data = {
                'date': cleaned_data['date'],
                'description': cleaned_data['description'],
                'amount': cleaned_data['amount'],
                'category': cleaned_data['category'],
                'account': cleaned_data['account'],
                'transaction_type': cleaned_data['transaction_type'],
                'tags': tags_list, # Passer la liste d'objets Tag
            }

            transaction_service.create_transaction(transaction_data)
            messages.success(request, "Transaction enregistrée avec succès!")
            return redirect('dashboard_view')
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement de la transaction: {e}")
    
    account_balances = transaction_service.get_account_balances()
    latest_transactions = transaction_service.get_latest_transactions(limit=10)
    
    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances,
        'transactions': latest_transactions,
        'form': form,
    }
    return render(request, 'webapp/index.html', context)


@require_GET
def load_subcategories(request):
    """
    Vue AJAX pour charger les sous-catégories en fonction d'une catégorie parente sélectionnée.
    """
    parent_id = request.GET.get('parent_category_id')
    subcategories = []
    if parent_id:
        try:
            parent_category = Category.objects.get(pk=parent_id)
            children = parent_category.children.all().order_by('name')
            for child in children:
                subcategories.append({'id': child.id, 'name': child.name})
        except Category.DoesNotExist:
            pass
    return JsonResponse(subcategories, safe=False)


@require_GET
def get_common_descriptions(request):
    """
    Vue AJAX pour récupérer les descriptions de transactions les plus courantes.
    """
    common_descriptions = Transaction.objects.filter(
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


@require_POST
def delete_selected_transactions(request):
    """
    Vue pour supprimer les transactions sélectionnées par l'utilisateur.
    """
    transaction_ids = request.POST.getlist('transaction_ids')
    
    if not transaction_ids:
        messages.error(request, "Aucune transaction sélectionnée pour la suppression.")
        return redirect('dashboard_view')

    try:
        with db_transaction.atomic():
            deleted_count, _ = Transaction.objects.filter(id__in=transaction_ids).delete()
        
        messages.success(request, f"{deleted_count} transaction(s) supprimée(s) avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression des transactions: {e}")
    
    return redirect('dashboard_view')


@require_GET
def get_transaction_form_for_edit(request, transaction_id):
    """
    Vue AJAX pour récupérer le formulaire d'édition d'une transaction spécifique.
    Le formulaire est pré-rempli avec les données de la transaction.
    """
    transaction = get_object_or_404(Transaction, pk=transaction_id)
    form = TransactionForm(instance=transaction)
    
    context = {'form': form, 'transaction_id': transaction_id}
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

