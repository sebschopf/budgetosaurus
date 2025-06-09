# webapp/views/transaction_actions.py
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from datetime import date
from django.contrib.auth.decorators import login_required # Importez le décorateur

from webapp.models import Transaction, Category, Budget, SavingGoal
from webapp.forms import TransactionForm
from webapp.services import TransactionService

@login_required # Protégez cette vue
@require_POST
def delete_selected_transactions(request):
    """
    Vue pour supprimer les transactions sélectionnées par l'utilisateur connecté.
    """
    transaction_ids = request.POST.getlist('transaction_ids')

    if not transaction_ids:
        messages.error(request, "Aucune transaction sélectionnée pour la suppression.")
        return redirect('dashboard_view')

    try:
        with Transaction.objects.atomic():
            # S'assurer que seules les transactions de l'utilisateur connecté sont supprimées
            deleted_count, _ = Transaction.objects.filter(id__in=transaction_ids, user=request.user).delete()

        messages.success(request, f"{deleted_count} transaction(s) supprimée(s) avec succès.")
    except Exception as e:
        messages.error(request, f"Erreur lors de la suppression des transactions: {e}")

    return redirect('dashboard_view')


@login_required # Protégez cette vue
@require_GET
def get_transaction_form_for_edit(request, transaction_id):
    """
    Vue AJAX pour récupérer le formulaire d'édition d'une transaction spécifique pour l'utilisateur connecté.
    Le formulaire est pré-rempli avec les données de la transaction.
    """
    # S'assurer que la transaction appartient à l'utilisateur connecté
    transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)
    # Passez l'utilisateur au formulaire pour filtrer les choix
    form = TransactionForm(instance=transaction, user=request.user)

    # Récupérer toutes les catégories pour le JS, incluant l'info is_fund_managed etc.
    all_categories_data = []
    all_subcategories_data = []

    current_year = date.today().year
    current_month = date.today().month
    # Filtrer les budgets et objectifs d'épargne par l'utilisateur
    budgeted_category_ids_for_current_period = set(
        Budget.objects.filter(
            user=request.user, # NOUVEAU
            period_type='M',
            start_date__year=current_year,
            start_date__month=current_month
        ).values_list('category__id', flat=True)
    )

    goal_linked_category_ids = set(
        SavingGoal.objects.filter(
            user=request.user, # NOUVEAU
            status='OU'
        ).values_list('category__id', flat=True)
    )

    # Filtrer les catégories par l'utilisateur connecté
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

    context = {
        'form': form,
        'transaction_id': transaction_id,
        'all_categories_data_json': json.dumps(all_categories_data),
        'all_subcategories_data_json': json.dumps(all_subcategories_data),
    }
    return render(request, 'webapp/dashboard_includes/edit_transaction_form_partial.html', context)


@login_required # Protégez cette vue
@require_GET
def suggest_transaction_categorization(request):
    """
    Vue AJAX pour suggérer une catégorie et des tags basés sur une description de transaction
    pour l'utilisateur connecté.
    """
    description = request.GET.get('description', '')
    transaction_service = TransactionService()
    # Passez request.user à la méthode de service
    suggestion = transaction_service.suggest_categorization(description, request.user)
    return JsonResponse(suggestion)
