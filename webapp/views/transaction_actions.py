import json
import logging
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from ..models import Transaction, Category
from ..forms.transaction_form import TransactionForm

# Ajoutez cette fonction en haut du fichier
from datetime import datetime

def format_date_for_input(date_obj):
    """Convertit une date en format ISO pour les inputs HTML5"""
    if date_obj:
        return date_obj.strftime('%Y-%m-%d')
    return ''

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET"])
def get_transaction_form(request, transaction_id):
    """
    Vue AJAX pour récupérer le formulaire d'édition d'une transaction
    """
    try:
        logger.info(f"Fetching form for transaction {transaction_id} for user {request.user.username}")
        
        # Récupérer la transaction
        transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
        logger.info(f"Transaction found: {transaction.description}")
        
        # Créer le formulaire
        form = TransactionForm(instance=transaction, user=request.user)
        
        # Formater la date pour l'input HTML5
        if hasattr(transaction, 'date'):
            form.initial['date'] = format_date_for_input(transaction.date)
        
        # Préparer les données de catégories
        all_categories_data = []
        all_subcategories_data = []
        
        # Récupérer les catégories principales
        categories = Category.objects.filter(
            user=request.user, 
            parent__isnull=True
        ).order_by('name')
        
        logger.info(f"Found {categories.count()} main categories")
        
        for cat in categories:
            all_categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'is_fund_managed': getattr(cat, 'is_fund_managed', False),
                'is_budgeted': getattr(cat, 'is_budgeted', False),
            })
            
            # Récupérer les sous-catégories
            subcategories = cat.children.filter(user=request.user).order_by('name')
            logger.info(f"Found {subcategories.count()} subcategories for {cat.name}")
            
            for child_cat in subcategories:
                all_subcategories_data.append({
                    'id': child_cat.id,
                    'name': child_cat.name,
                    'parent': cat.id,
                    'is_fund_managed': getattr(child_cat, 'is_fund_managed', False),
                    'is_budgeted': getattr(child_cat, 'is_budgeted', False),
                })

        logger.info(f"Total: {len(all_categories_data)} categories and {len(all_subcategories_data)} subcategories")

        # Rendre le template
        form_html = render_to_string(
            'webapp/dashboard_includes/edit_transaction_form_partial.html',
            {
                'form': form,
                'transaction': transaction,
                'transaction_id': transaction_id,
                'all_categories_data_json': mark_safe(json.dumps(all_categories_data)),
                'all_subcategories_data_json': mark_safe(json.dumps(all_subcategories_data)),
            },
            request=request
        )
        
        logger.info(f"Form HTML generated successfully, length: {len(form_html)}")
        
        return JsonResponse({
            'success': True,
            'form_html': form_html
        })
        
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found for user {request.user.username}")
        return JsonResponse({
            'success': False,
            'error': 'Transaction non trouvée'
        }, status=404)
    except Exception as e:
        logger.error(f"Error fetching transaction form: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors du chargement du formulaire: {str(e)}'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def edit_transaction(request, transaction_id):
    """
    Vue pour traiter la soumission du formulaire d'édition
    """
    try:
        logger.info(f"Editing transaction {transaction_id} for user {request.user.username}")
        
        transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
        
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        
        if form.is_valid():
            # Assigner la catégorie finale (principale ou sous-catégorie)
            final_category = form.cleaned_data.get('final_category')
            if final_category:
                transaction.category = final_category
            
            saved_transaction = form.save()
            logger.info(f"Transaction {transaction_id} updated successfully")
            
            return JsonResponse({
                'success': True,
                'message': 'Transaction mise à jour avec succès'
            })
        else:
            logger.warning(f"Form validation failed for transaction {transaction_id}: {form.errors}")
            
            # Retourner le formulaire avec les erreurs
            all_categories_data = []
            all_subcategories_data = []
            
            for cat in Category.objects.filter(user=request.user, parent__isnull=True).order_by('name'):
                all_categories_data.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_fund_managed': getattr(cat, 'is_fund_managed', False),
                    'is_budgeted': getattr(cat, 'is_budgeted', False),
                })
                
                for child_cat in cat.children.filter(user=request.user).order_by('name'):
                    all_subcategories_data.append({
                        'id': child_cat.id,
                        'name': child_cat.name,
                        'parent': cat.id,
                        'is_fund_managed': getattr(child_cat, 'is_fund_managed', False),
                        'is_budgeted': getattr(child_cat, 'is_budgeted', False),
                    })

            form_html = render_to_string(
                'webapp/dashboard_includes/edit_transaction_form_partial.html',
                {
                    'form': form,
                    'transaction': transaction,
                    'transaction_id': transaction_id,
                    'all_categories_data_json': mark_safe(json.dumps(all_categories_data)),
                    'all_subcategories_data_json': mark_safe(json.dumps(all_subcategories_data)),
                },
                request=request
            )
            
            return JsonResponse({
                'success': False, 
                'errors_html': form_html,
                'errors': form.errors
            })
            
    except Transaction.DoesNotExist:
        logger.error(f"Transaction {transaction_id} not found for user {request.user.username}")
        return JsonResponse({
            'success': False,
            'error': 'Transaction non trouvée'
        }, status=404)
    except Exception as e:
        logger.error(f"Error editing transaction: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Erreur lors de la modification: {str(e)}'
        }, status=500)

@login_required
def delete_transaction(request, transaction_id):
    """
    Vue pour supprimer une transaction
    """
    try:
        transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
        transaction_desc = transaction.description
        transaction.delete()
        
        messages.success(request, f'Transaction "{transaction_desc}" supprimée avec succès.')
        logger.info(f"Transaction {transaction_id} deleted by user {request.user.username}")
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
        logger.error(f"Error deleting transaction {transaction_id}: {str(e)}")
    
    return redirect('review_transactions_view')

@login_required
@require_http_methods(["POST"])
def delete_selected_transactions(request):
    """
    Vue pour supprimer plusieurs transactions sélectionnées
    """
    try:
        transaction_ids = request.POST.getlist('transaction_ids')
        if not transaction_ids:
            messages.warning(request, 'Aucune transaction sélectionnée.')
            return redirect('review_transactions_view')
        
        # Supprimer les transactions appartenant à l'utilisateur
        deleted_count = Transaction.objects.filter(
            id__in=transaction_ids,
            user=request.user
        ).delete()[0]
        
        messages.success(request, f'{deleted_count} transaction(s) supprimée(s) avec succès.')
        logger.info(f"{deleted_count} transactions deleted by user {request.user.username}")
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
        logger.error(f"Error deleting selected transactions: {str(e)}")
    
    return redirect('review_transactions_view')

def suggest_transaction_categorization(request):
    """
    Vue pour suggérer une catégorisation automatique des transactions
    (À implémenter selon vos besoins)
    """
    return JsonResponse({'message': 'Fonctionnalité à implémenter'})
