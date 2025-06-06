# webapp/views/review_transactions.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
import json # Importez json
from datetime import date # Importez date

from webapp.models import Transaction, Category, Account, Budget, SavingGoal # Importez Budget et SavingGoal
from webapp.forms import TransactionForm
from webapp.services import TransactionService # Importez le TransactionService


def review_transactions_view(request):
    """
    Vue affichant les transactions qui nécessitent une révision (par exemple, sans catégorie).
    Permet de les modifier et de les catégoriser.
    """
    transactions_to_review = Transaction.objects.filter(category__isnull=True).order_by('-date', '-created_at')

    context = {
        'page_title': 'Transactions à Revoir',
        'transactions_to_review': transactions_to_review,
    }
    return render(request, 'webapp/review_transactions.html', context)


@require_POST
def update_transaction_category(request, transaction_id):
    """
    Vue AJAX pour mettre à jour la catégorie et d'autres détails d'une transaction spécifique.
    Retourne une réponse JSON (succès ou formulaire avec erreurs).
    Utilise TransactionService.update_transaction.
    """
    transaction = get_object_or_404(Transaction, pk=transaction_id)
    form = TransactionForm(request.POST, instance=transaction)
    transaction_service = TransactionService() # Instanciez le service

    if form.is_valid():
        try:
            # Les données nettoyées du formulaire incluent maintenant 'tags' comme QuerySet d'objets Tag
            cleaned_data = form.cleaned_data
            tags_list = list(cleaned_data.pop('tags')) # Convertir le QuerySet en liste

            # Récupérer la catégorie finale déterminée par le formulaire
            final_category = cleaned_data.pop('final_category')

            update_data = {
                'date': cleaned_data['date'],
                'description': cleaned_data['description'],
                'amount': cleaned_data['amount'],
                'category': final_category, # Utiliser la catégorie finale
                'account': cleaned_data['account'],
                'transaction_type': cleaned_data['transaction_type'],
                'tags': tags_list, # Passer la liste d'objets Tag
            }
            
            transaction_service.update_transaction(transaction, update_data) # Utilisez la nouvelle méthode du service
            messages.success(request, f"Transaction '{transaction.description}' mise à jour avec succès.")
            return JsonResponse({'success': True})
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour de la transaction: {e}")
            # Si une erreur survient, nous devons re-rendre le formulaire avec les erreurs
            
            # Ajoutez les flags pour le re-rendu du formulaire avec erreurs
            all_categories_data = []
            all_subcategories_data = []

            current_year = date.today().year
            current_month = date.today().month
            budgeted_category_ids_for_current_period = set(
                Budget.objects.filter(
                    period_type='M', 
                    start_date__year=current_year,
                    start_date__month=current_month
                ).values_list('category__id', flat=True)
            )
            goal_linked_category_ids = set(
                SavingGoal.objects.filter(
                    status='OU' 
                ).values_list('category__id', flat=True)
            )

            for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
                is_budgeted_for_display = cat.is_budgeted 
                is_fund_managed_for_display = cat.is_fund_managed 
                is_goal_linked_for_display = cat.id in goal_linked_category_ids 

                all_categories_data.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_fund_managed': is_fund_managed_for_display,
                    'is_budgeted': is_budgeted_for_display,
                    'is_goal_linked': is_goal_linked_for_display
                })
                for child_cat in cat.children.all().order_by('name'):
                    child_is_budgeted_for_display = child_cat.is_budgeted 
                    child_is_fund_managed_for_display = child_cat.is_fund_managed 
                    child_is_goal_linked_for_display = child_cat.id in goal_linked_category_ids 

                    all_subcategories_data.append({
                        'id': child_cat.id,
                        'name': child_cat.name,
                        'parent': cat.id,
                        'is_fund_managed': child_is_fund_managed_for_display,
                        'is_budgeted': child_is_budgeted_for_display,
                        'is_goal_linked': child_is_goal_linked_for_display
                    })

            form_html = render_to_string(
                'webapp/dashboard_includes/edit_transaction_form_partial.html',
                {
                    'form': form, 
                    'transaction_id': transaction_id,
                    'all_categories_data_json': json.dumps(all_categories_data), # Pour la modale d'édition
                    'all_subcategories_data_json': json.dumps(all_subcategories_data), # Pour la modale d'édition
                },
                request=request
            )
            return JsonResponse({'success': False, 'errors_html': form_html, 'message': str(e)})
    else:
        # Pour une requête AJAX avec erreurs, renvoyer le formulaire rendu avec les erreurs
        all_categories_data = []
        all_subcategories_data = []

        current_year = date.today().year
        current_month = date.today().month
        budgeted_category_ids_for_current_period = set(
            Budget.objects.filter(
                period_type='M', 
                start_date__year=current_year,
                start_date__month=current_month
            ).values_list('category__id', flat=True)
        )
        goal_linked_category_ids = set(
            SavingGoal.objects.filter(
                status='OU' 
            ).values_list('category__id', flat=True)
        )

        for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
            is_budgeted_for_display = cat.is_budgeted 
            is_fund_managed_for_display = cat.is_fund_managed 
            is_goal_linked_for_display = cat.id in goal_linked_category_ids 

            all_categories_data.append({
                'id': cat.id,
                'name': cat.name,
                'is_fund_managed': is_fund_managed_for_display,
                'is_budgeted': is_budgeted_for_display,
                'is_goal_linked': is_goal_linked_for_display
            })
            for child_cat in cat.children.all().order_by('name'):
                child_is_budgeted_for_display = child_cat.is_budgeted 
                child_is_fund_managed_for_display = child_cat.is_fund_managed 
                child_is_goal_linked_for_display = child_cat.id in goal_linked_category_ids 

                all_subcategories_data.append({
                    'id': child_cat.id,
                    'name': child_cat.name,
                    'parent': cat.id,
                    'is_fund_managed': child_is_fund_managed_for_display,
                    'is_budgeted': child_is_budgeted_for_display,
                    'is_goal_linked': child_is_goal_linked_for_display
                })

        form_html = render_to_string(
            'webapp/dashboard_includes/edit_transaction_form_partial.html',
            {
                'form': form, 
                'transaction_id': transaction_id,
                'all_categories_data_json': json.dumps(all_categories_data), 
                'all_subcategories_data_json': json.dumps(all_subcategories_data), 
            },
            request=request
        )
        # Renvoyer un JSON indiquant l'échec et le HTML du formulaire avec erreurs
        return JsonResponse({'success': False, 'errors_html': form_html})
