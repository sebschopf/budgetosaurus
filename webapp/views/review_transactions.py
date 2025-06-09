# webapp/views/review_transactions.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.template.loader import render_to_string
import json
from datetime import date
from django.contrib.auth.decorators import login_required 
from webapp.models import Transaction, Category, Account, Budget, SavingGoal
from webapp.forms import TransactionForm
from webapp.services import TransactionService


@login_required
def review_transactions_view(request):
    """
    Vue affichant les transactions qui nécessitent une révision (par exemple, sans catégorie)
    pour l'utilisateur connecté. Permet de les modifier et de les catégoriser.
    """
    # Filtrer les transactions par l'utilisateur
    transactions_to_review = Transaction.objects.filter(user=request.user, category__isnull=True).order_by('-date', '-created_at')

    context = {
        'page_title': 'Transactions à Revoir',
        'transactions_to_review': transactions_to_review,
    }
    return render(request, 'webapp/review_transactions.html', context)


@login_required
def update_transaction_category(request, transaction_id):
    """
    Vue AJAX pour mettre à jour la catégorie et d'autres détails d'une transaction spécifique
    pour l'utilisateur connecté.
    Retourne une réponse JSON (succès ou formulaire avec erreurs).
    Utilise TransactionService.update_transaction.
    """
    # S'assurer que la transaction appartient à l'utilisateur connecté
    transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
    # Passer l'utilisateur au formulaire pour filtrer les choix
    form = TransactionForm(request.POST, instance=transaction, user=request.user)
    transaction_service = TransactionService()

    if form.is_valid():
        try:
            cleaned_data = form.cleaned_data
            tags_list = list(cleaned_data.pop('tags'))

            final_category = cleaned_data.pop('final_category')

            update_data = {
                'date': cleaned_data['date'],
                'description': cleaned_data['description'],
                'amount': cleaned_data['amount'],
                'category': final_category,
                'account': cleaned_data['account'],
                'transaction_type': cleaned_data['transaction_type'],
                'tags': tags_list,
            }

            # Passer request.user à la méthode update_transaction
            transaction_service.update_transaction(transaction, update_data, request.user)
            messages.success(request, f"Transaction '{transaction.description}' mise à jour avec succès.")
            return JsonResponse({'success': True})
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour de la transaction: {e}")
            # Si une erreur survient, nous devons re-rendre le formulaire avec les erreurs

            # Filtrer toutes les catégories par l'utilisateur pour le re-rendu
            all_categories_data = []
            all_subcategories_data = []

            current_year = date.today().year
            current_month = date.today().month
            budgeted_category_ids_for_current_period = set(
                Budget.objects.filter(
                    user=request.user, 
                    period_type='M',
                    start_date__year=current_year,
                    start_date__month=current_month
                ).values_list('category__id', flat=True)
            )
            goal_linked_category_ids = set(
                SavingGoal.objects.filter(
                    user=request.user, 
                    status='OU'
                ).values_list('category__id', flat=True)
            )

            for cat in Category.objects.filter(user=request.user, parent__isnull=True).order_by('name'):
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
                # Filtrer les sous-catégories par l'utilisateur
                for child_cat in cat.children.filter(user=request.user).order_by('name'):
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
            return JsonResponse({'success': False, 'errors_html': form_html, 'message': str(e)})
    else:
        # Pour une requête AJAX avec erreurs, renvoyer le formulaire rendu avec les erreurs
        # Filtrer toutes les catégories par l'utilisateur pour le re-rendu
        all_categories_data = []
        all_subcategories_data = []

        current_year = date.today().year
        current_month = date.today().month
        budgeted_category_ids_for_current_period = set(
            Budget.objects.filter(
                user=request.user,
                period_type='M',
                start_date__year=current_year,
                start_date__month=current_month
            ).values_list('category__id', flat=True)
        )
        goal_linked_category_ids = set(
            SavingGoal.objects.filter(
                user=request.user,
                status='OU'
            ).values_list('category__id', flat=True)
        )

        for cat in Category.objects.filter(user=request.user, parent__isnull=True).order_by('name'):
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
            # Filtrer les sous-catégories par l'utilisateur
            for child_cat in cat.children.filter(user=request.user).order_by('name'):
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
        return JsonResponse({'success': False, 'errors_html': form_html})
