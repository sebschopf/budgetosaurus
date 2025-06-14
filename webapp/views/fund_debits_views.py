# webapp/views/fund_debits_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required

from webapp.models import Category, Transaction, Fund, FundDebitRecord, FundDebitLine
from webapp.forms import FundDebitRecordForm, FundDebitLineFormset

@login_required
@require_GET
def debit_funds_view(request, transaction_id):
    """
    Vue pour débiter des fonds pour une transaction de dépense (type OUT).
    Cette vue affichera un formulaire pour définir les lignes de débit.
    Accessible uniquement aux utilisateurs connectés.
    """
    # S'assurer que la transaction appartient à l'utilisateur connecté
    original_transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)

    # Vérifier que la transaction est bien une dépense et n'a pas déjà d'enregistrement de débit de fonds
    if original_transaction.transaction_type != 'OUT':
        messages.error(request, "Seules les transactions de type 'Dépense' peuvent débiter des fonds.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'fund_debit_record'):
        messages.warning(request, f"La transaction '{original_transaction.description}' a déjà un débit de fonds associé.")
        return redirect('all_transactions_summary_view')

    # Créer une instance vide du formulaire principal de FundDebitRecord
    # Passer l'utilisateur au formulaire pour filtrer les choix si nécessaire (bien que FundDebitRecordForm n'ait pas de ModelChoiceField)
    form = FundDebitRecordForm(initial={'notes': f"Débit de fonds pour: {original_transaction.description}"})
    # Créer un formset pour les lignes de débit de fonds
    # Passer l'utilisateur au formset pour filtrer les choix de catégorie
    formset = FundDebitLineFormset(user=request.user)

    # Récupérer toutes les catégories qui gèrent un fonds POUR L'UTILISATEUR CONNECTÉ
    fund_managed_categories = []
    for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
        fund_managed_categories.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })

    context = {
        'page_title': 'Débiter des Fonds',
        'original_transaction': original_transaction,
        'form': form,
        'formset': formset,
        'fund_managed_categories_json': json.dumps(fund_managed_categories),
    }
    return render(request, 'webapp/debit_funds.html', context)


@login_required
@require_POST
def process_fund_debit(request, transaction_id):
    """
    Gère la soumission du formulaire de débit de fonds.
    Crée l'objet FundDebitRecord et ses lignes pour l'utilisateur connecté, puis met à jour les fonds.
    """
    # S'assurer que la transaction originale appartient à l'utilisateur connecté
    original_transaction = get_object_or_404(Transaction, pk=transaction_id, user=request.user)

    if original_transaction.transaction_type != 'OUT':
        messages.error(request, "Opération invalide: Seules les transactions de type 'Dépense' peuvent débiter des fonds.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'fund_debit_record'):
        messages.error(request, f"Cette transaction a déjà un enregistrement de débit de fonds associé.")
        return redirect('all_transactions_summary_view')

    # Passer l'utilisateur aux formulaires pour filtrer les choix
    form = FundDebitRecordForm(request.POST) # FundDebitRecordForm n'a pas de ModelChoiceField sur 'user'
    formset = FundDebitLineFormset(request.POST, user=request.user) # Passer l'utilisateur au formset

    if form.is_valid() and formset.is_valid():
        total_debited_amount = Decimal('0.00')
        lines_to_create = []

        for line_form in formset:
            if not line_form.cleaned_data.get('DELETE', False):
                debited_amount = line_form.cleaned_data['amount']
                category = line_form.cleaned_data['category']
                notes = line_form.cleaned_data.get('notes', '')

                # Vérifier que la catégorie gère bien un fonds POUR L'UTILISATEUR CONNECTÉ
                # La catégorie doit aussi appartenir à l'utilisateur
                if not category.is_fund_managed or category.user != request.user:
                    messages.error(request, f"La catégorie '{category.name}' ne gère pas de fonds ou n'appartient pas à votre compte et ne peut pas être débitée directement.")
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
                        'page_title': 'Débiter des Fonds',
                        'original_transaction': original_transaction,
                        'form': form,
                        'formset': formset, # Le formset avec les erreurs
                        'fund_managed_categories_json': json.dumps(fund_managed_categories),
                    }
                    return render(request, 'webapp/debit_funds.html', context)

                total_debited_amount += debited_amount
                lines_to_create.append({
                    'category': category,
                    'amount': debited_amount,
                    'notes': notes,
                })

        if total_debited_amount > abs(original_transaction.amount) + Decimal('0.01'):
            messages.error(request, f"Le montant total débité ({total_debited_amount:.2f} CHF) dépasse le montant de la transaction originale ({abs(original_transaction.amount):.2f} CHF).")
            fund_managed_categories = []
            # Filtrer les catégories par l'utilisateur pour le re-rendu
            for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
                fund_managed_categories.append({
                    'id': cat.id,
                    'name': cat.name,
                    'is_fund_managed': cat.is_fund_managed
                })
            context = {
                'page_title': 'Débiter des Fonds',
                'original_transaction': original_transaction,
                'form': form,
                'formset': formset, # Le formset avec les erreurs
                'fund_managed_categories_json': json.dumps(fund_managed_categories),
            }
            return render(request, 'webapp/debit_funds.html', context)

        try:
            with Transaction.objects.atomic():
                # Créer l'objet FundDebitRecord
                # Assigner l'utilisateur au FundDebitRecord
                fund_debit_record = FundDebitRecord.objects.create(
                    user=request.user, # NOUVEAU
                    transaction=original_transaction,
                    total_debited_amount=total_debited_amount,
                    notes=form.cleaned_data.get('notes', '')
                )

                # Créer les lignes de débit et mettre à jour les fonds
                for line_data in lines_to_create:
                    # Assigner l'utilisateur au FundDebitLine
                    FundDebitLine.objects.create(
                        user=request.user, # NOUVEAU
                        fund_debit_record=fund_debit_record,
                        category=line_data['category'],
                        amount=line_data['amount'],
                        notes=line_data['notes']
                    )
                    # Mettre à jour le solde du fonds
                    # Passer l'utilisateur au FundManager
                    Fund.objects.subtract_funds_from_category(line_data['category'], line_data['amount'], request.user)

            messages.success(request, f"Dépense de {abs(original_transaction.amount):.2f} CHF débitée avec succès des fonds.")
            return redirect('all_transactions_summary_view')

        except Exception as e:
            messages.error(request, f"Erreur lors du débit des fonds: {e}")
    else:
        messages.error(request, "Veuillez corriger les erreurs dans le formulaire de débit de fonds.")

    # Si le formulaire n'est pas valide ou s'il y a une erreur, re-rendre la page de débit
    fund_managed_categories = []
    # Filtrer les catégories par l'utilisateur pour le re-rendu
    for cat in Category.objects.filter(user=request.user, is_fund_managed=True).order_by('name'):
        fund_managed_categories.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })

    context = {
        'page_title': 'Débiter des Fonds',
        'original_transaction': original_transaction,
        'form': form, # Le formulaire avec les erreurs
        'formset': formset, # Le formset avec les erreurs
        'fund_managed_categories_json': json.dumps(fund_managed_categories),
    }
    return render(request, 'webapp/debit_funds.html', context)
