# webapp/views/fund_allocations_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from webapp.models import Category, Transaction, Fund, Allocation, AllocationLine
from webapp.forms import AllocationForm, AllocationLineFormset

@login_required
@require_GET
def allocate_income_view(request, transaction_id):
    """
    Vue pour allouer une transaction de revenu (type IN) à différents fonds.
    Cette vue affichera un formulaire pour définir les lignes d'allocation.
    Accessible uniquement aux utilisateurs connectés.
    """
    # S'assurer que la transaction appartient à l'utilisateur connecté
    original_transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)

    # Vérifier que la transaction est bien un revenu et n'a pas déjà d'allocation
    # Les messages d'erreur spécifiques.
    if original_transaction.transaction_type != 'IN':
        messages.error(request, "Seules les transactions de type 'Revenu' peuvent être allouées.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'allocation'):
        messages.warning(request, f"La transaction '{original_transaction.description}' a déjà été allouée.")
        return redirect('all_transactions_summary_view')

    # Créer une instance vide du formulaire principal d'Allocation
    # Passer l'utilisateur au formulaire pour filtrer les choix si nécessaire (bien que AllocationForm ne filtre pas de ModelChoiceField)
    form = AllocationForm(initial={'notes': f"Allocation pour: {original_transaction.description}"})
    # Créer un formset pour les lignes d'allocation
    # Passer l'utilisateur au formset pour filtrer les choix de catégorie
    formset = AllocationLineFormset(user=request.user)

    # Récupérer toutes les catégories qui gèrent un fonds POUR L'UTILISATEUR CONNECTÉ
    fund_managed_categories = []
    for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
        fund_managed_categories.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })

    context = {
        'page_title': 'Allouer un Revenu aux Fonds',
        'original_transaction': original_transaction,
        'form': form,
        'formset': formset,
        'fund_managed_categories_json': json.dumps(fund_managed_categories),
    }
    return render(request, 'webapp/allocate_income.html', context)


@login_required 
@require_POST
def process_allocation_income(request, transaction_id):
    """
    Gère la soumission du formulaire d'allocation de revenu.
    Crée l'objet Allocation et ses lignes pour l'utilisateur connecté, puis met à jour les fonds.
    """
    # S'assurer que la transaction originale appartient à l'utilisateur connecté
    original_transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)

    if original_transaction.transaction_type != 'IN':
        messages.error(request, "Opération invalide: Seules les transactions de type 'Revenu' peuvent être allouées.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'allocation'):
        messages.error(request, f"Cette transaction a déjà été allouée.")
        return redirect('all_transactions_summary_view')

    # Passer l'utilisateur aux formulaires pour filtrer les choix
    form = AllocationForm(request.POST) # AllocationForm n'a pas de ModelChoiceField sur 'user'
    formset = AllocationLineFormset(request.POST, user=request.user) # Passer l'utilisateur au formset

    if form.is_valid() and formset.is_valid():
        total_allocated_amount = Decimal('0.00')
        lines_to_create = []

        for line_form in formset:
            if not line_form.cleaned_data.get('DELETE', False):
                allocated_amount = line_form.cleaned_data['amount']
                category = line_form.cleaned_data['category']
                notes = line_form.cleaned_data.get('notes', '')

                # Vérifier que la catégorie gère bien un fonds POUR L'UTILISATEUR CONNECTÉ
                # La catégorie doit aussi appartenir à l'utilisateur
                if not category.is_fund_managed or category.user != request.user:
                    messages.error(request, f"La catégorie '{category.name}' ne gère pas de fonds ou n'appartient pas à votre compte et ne peut pas recevoir d'allocation directe.")
                    # Re-rendre la page avec les erreurs
                    fund_managed_categories = []
                    # Filtrer les catégories par l'utilisateur pour le re-rendu
                    for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
                        fund_managed_categories.append({
                            'id': cat.id,
                            'name': cat.name,
                            'is_fund_managed': cat.is_fund_managed
                        })
                    context = {
                        'page_title': 'Allouer un Revenu aux Fonds',
                        'original_transaction': original_transaction,
                        'form': form,
                        'formset': formset, # Le formset avec les erreurs
                        'fund_managed_categories_json': json.dumps(fund_managed_categories),
                    }
                    return render(request, 'webapp/allocate_income.html', context)

                total_allocated_amount += allocated_amount
                lines_to_create.append({
                    'category': category,
                    'amount': allocated_amount,
                    'notes': notes,
                })

        if total_allocated_amount > abs(original_transaction.amount) + Decimal('0.01'):
            messages.error(request, f"Le montant total alloué ({total_allocated_amount:.2f} CHF) dépasse le montant de la transaction originale ({abs(original_transaction.amount):.2f} CHF).")
            fund_managed_categories = []
            # Filtrer les catégories par l'utilisateur pour le re-rendu
            for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
                fund_managed_categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_fund_managed': cat.is_fund_managed
                })
            context = {
                'page_title': 'Allouer un Revenu aux Fonds',
                'original_transaction': original_transaction,
                'form': form,
                'formset': formset, # Le formset avec les erreurs
                'fund_managed_categories_json': json.dumps(fund_managed_categories),
            }
            return render(request, 'webapp/allocate_income.html', context)

        try:
            with Transaction.objects.atomic():
                # Créer l'objet Allocation
                # Assigner l'utilisateur à l'Allocation
                allocation = Allocation.objects.create(
                    user=request.user, # NOUVEAU
                    transaction=original_transaction,
                    total_allocated_amount=total_allocated_amount,
                    notes=form.cleaned_data.get('notes', '')
                )

                # Créer les lignes d'allocation et mettre à jour les fonds
                for line_data in lines_to_create:
                    # Assigner l'utilisateur à l'AllocationLine
                    AllocationLine.objects.create(
                        user=request.user, # NOUVEAU
                        allocation=allocation,
                        category=line_data['category'],
                        amount=line_data['amount'],
                        notes=line_data['notes']
                    )
                    # Mettre à jour le solde du fonds
                    # Passer l'utilisateur au FundManager
                    Fund.objects.add_funds_to_category(line_data['category'], line_data['amount'], request.user)

            messages.success(request, f"Revenu de {original_transaction.amount:.2f} CHF alloué avec succès aux fonds.")
            return redirect('all_transactions_summary_view')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'allocation du revenu: {e}")
    else:
        messages.error(request, "Veuillez corriger les erreurs dans le formulaire d'allocation.")

    # Si le formulaire n'est pas valide ou s'il y a une erreur, re-rendre la page d'allocation
    fund_managed_categories = []
    # Filtrer les catégories par l'utilisateur pour le re-rendu
    for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
        fund_managed_categories.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })

    context = {
        'page_title': 'Allouer un Revenu aux Fonds',
        'original_transaction': original_transaction,
        'form': form, # Le formulaire avec les erreurs
        'formset': formset, # Le formset avec les erreurs
        'fund_managed_categories_json': json.dumps(fund_managed_categories),
    }
    return render(request, 'webapp/allocate_income.html', context)
