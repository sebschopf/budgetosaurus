# webapp/views/split_transactions_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from decimal import Decimal

from webapp.models import Transaction, Category # Importez les modèles nécessaires
from webapp.forms import SplitTransactionFormset # Importez le formset de division
from webapp.services import TransactionService # Importez le service

@require_GET
def split_transaction_view(request, transaction_id=None):
    """
    Vue pour la fonctionnalité de division de transaction.
    Si un transaction_id est fourni, le formulaire est pré-rempli avec les données de la transaction.
    """
    original_transaction = None
    formset = SplitTransactionFormset() # Formset vide par défaut

    if transaction_id:
        original_transaction = get_object_or_404(Transaction, pk=transaction_id)
        # Pré-remplir la première ligne du formset avec la description de la transaction originale
        # et une quantité égale à l'originale si c'est une dépense.
        if original_transaction.transaction_type == 'OUT': # Uniquement pour les dépenses
            initial_data = []
            initial_data.append({
                'description': original_transaction.description,
                'amount': abs(original_transaction.amount), # Montant absolu pour la saisie
                'main_category': original_transaction.category.parent.id if original_transaction.category and original_transaction.category.parent else (original_transaction.category.id if original_transaction.category else None),
                'subcategory': original_transaction.category.id if original_transaction.category and original_transaction.category.parent else None,
            })
            formset = SplitTransactionFormset(initial=initial_data)

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
        'page_title': 'Diviser une Transaction',
        'original_transaction': original_transaction,
        'formset': formset,
        'all_categories_data_json': json.dumps(all_categories_data), # Données pour le JS
        'all_subcategories_data_json': json.dumps(all_subcategories_data), # Données pour le JS
    }
    return render(request, 'webapp/split_transaction.html', context)

@require_POST
def process_split_transaction(request):
    """
    Gère la soumission du formulaire de division de transaction.
    Crée de nouvelles transactions et supprime l'originale.
    """
    original_transaction_id = request.POST.get('original_transaction_id')
    original_transaction = get_object_or_404(Transaction, pk=original_transaction_id)

    formset = SplitTransactionFormset(request.POST)
    transaction_service = TransactionService()

    if formset.is_valid():
        split_lines_data = []
        for form in formset:
            if not form.cleaned_data.get('DELETE', False): # Ignorer les lignes marquées pour suppression
                # La catégorie finale est dans 'final_category' grâce à la méthode clean du formulaire
                final_category = form.cleaned_data['final_category']
                split_lines_data.append({
                    'description': form.cleaned_data['description'],
                    'amount': form.cleaned_data['amount'],
                    'category': final_category,
                    'tags': [], 
                })
        
        try:
            transaction_service.split_transaction(original_transaction, split_lines_data)
            messages.success(request, "Transaction divisée et enregistrée avec succès!")
            return redirect('all_transactions_summary_view')
        except ValueError as e:
            messages.error(request, f"Erreur de division: {e}")
        except Exception as e:
            messages.error(request, f"Erreur inattendue lors de la division: {e}")
    else:
        messages.error(request, "Veuillez corriger les erreurs dans le formulaire de division.")
    
    # Si le formulaire n'est pas valide ou s'il y a une erreur, re-rendre la page de division
    # avec les erreurs et les données du formset.
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
        'page_title': 'Diviser une Transaction',
        'original_transaction': original_transaction,
        'formset': formset, # Le formset avec les erreurs
        'all_categories_data_json': json.dumps(all_categories_data), 
        'all_subcategories_data_json': json.dumps(all_subcategories_data),
    }
    return render(request, 'webapp/split_transaction.html', context)

