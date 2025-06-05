# webapp/views/transactions.py
from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db.models import F
from django.db import transaction as db_transaction
from datetime import date, timedelta
import calendar
import json
from decimal import Decimal # Assurez-vous d'importer Decimal

from webapp.models import Category, Transaction, Account, Tag, Allocation, AllocationLine, Fund # Importez Allocation, AllocationLine, Fund
from webapp.forms import TransactionForm, SplitTransactionFormset, AllocationForm, AllocationLineFormset # Importez les formulaires d'allocation
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

            # Récupérer la catégorie finale déterminée par le formulaire (qui peut être main_category ou subcategory)
            final_category = cleaned_data.pop('final_category')

            transaction_data = {
                'date': cleaned_data['date'],
                'description': cleaned_data['description'],
                'amount': cleaned_data['amount'],
                'category': final_category, # Utiliser la catégorie finale
                'account': cleaned_data['account'],
                'transaction_type': cleaned_data['transaction_type'],
                'tags': tags_list, # Passer la liste d'objets Tag
            }

            transaction_service.create_transaction(transaction_data)
            messages.success(request, "Transaction enregistrée avec succès!")
            return redirect('dashboard_view')
        except Exception as e:
            messages.error(request, f"Erreur lors de l'enregistrement de la transaction: {e}")
    
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
        'page_title': 'Tableau de Bord',
        'account_balances': transaction_service.get_account_balances(), # Actualiser les soldes
        'transactions': transaction_service.get_latest_transactions(limit=10), # Actualiser les transactions
        'form': form, # Re-passer le formulaire avec les erreurs
        'all_categories_data_json': json.dumps(all_categories_data),
        'all_subcategories_data_json': json.dumps(all_subcategories_data),
    }
    return render(request, 'webapp/index.html', context)


@require_GET
def load_subcategories(request):
    """
    Vue AJAX pour charger les sous-catégories en fonction d'une catégorie parente sélectionnée,
    incluant le statut is_fund_managed.
    """
    parent_id = request.GET.get('parent_category_id')
    subcategories = []
    if parent_id:
        try:
            parent_category = Category.objects.get(pk=parent_id)
            children = parent_category.children.all().order_by('name')
            for child in children:
                subcategories.append({
                    'id': child.id, 
                    'name': child.name, 
                    'is_fund_managed': child.is_fund_managed # Ajoutez cette information
                })
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


@require_GET
def category_transactions_summary_view(request, year=None, month=None):
    """
    Vue affichant un récapitulatif des transactions,
    regroupées par catégories qui sont désignées comme "gérant un fonds" (`is_fund_managed`).
    Affiche les transactions individuelles pour chaque catégorie pour la période spécifiée.
    """
    today = date.today()
    
    # Déterminer l'année et le mois à filtrer
    if year is None:
        selected_year = today.year
    else:
        selected_year = int(year) # Convertir en int
        
    selected_month = None # Initialiser à None pour le cas "année courante"

    if month is None:
        # Si le mois n'est pas spécifié, on est en mode "année courante"
        period_type = 'year'
        start_date = date(selected_year, 1, 1)
        # Pour l'année courante, la date de fin doit être le 31 décembre de cette année.
        end_date = date(selected_year, 12, 31) 
        period_display = f"Année {selected_year}"
    else:
        # Si le mois est spécifié, on est en mode "mois courant"
        period_type = 'month'
        selected_month = int(month) # Convertir en int
        start_date = date(selected_year, selected_month, 1)
        # Calculer le dernier jour du mois
        _, last_day = calendar.monthrange(selected_year, selected_month)
        end_date = date(selected_year, selected_month, last_day)
        period_display = f"{calendar.month_name[selected_month]} {selected_year}"


    # Récupérer uniquement les catégories marquées comme gérant un fonds
    fund_managed_categories = Category.objects.filter(is_fund_managed=True).order_by('name')

    category_transactions_summary = []

    for category in fund_managed_categories:
        # Obtenir les IDs de la catégorie et de ses enfants
        category_ids_for_query = [category.id] + list(category.children.values_list('id', flat=True))

        # Filtrer les transactions pour la période donnée
        transactions_in_category = Transaction.objects.filter(
            category__id__in=category_ids_for_query,
            date__gte=start_date, # Date supérieure ou égale à la date de début
            date__lte=end_date # Date inférieure ou égale à la date de fin
        ).order_by('date', 'created_at') # Ordonner pour un affichage cohérent

        # Si des transactions existent pour cette catégorie dans la période
        if transactions_in_category.exists():
            transaction_list_data = []
            for transaction in transactions_in_category:
                transaction_list_data.append({
                    'date': transaction.date,
                    'description': transaction.description,
                    'amount': transaction.amount, # Le montant est déjà normalisé (négatif pour dépenses)
                    'transaction_type': transaction.get_transaction_type_display(),
                    'account_name': transaction.account.name,
                    'account_currency': transaction.account.currency,
                })
            
            category_transactions_summary.append({
                'category_name': category.name,
                'transactions': transaction_list_data
            })
    
    context = {
        'page_title': 'Récapitulatif des Transactions par Catégorie',
        'current_period_display': period_display,
        'category_transactions_summary': category_transactions_summary,
        'today_year': today.year, # Pour les boutons "Mois Courant" / "Année Courante"
        'today_month': today.month,
        'selected_year': selected_year, # Pour savoir quelle période est actuellement affichée
        'selected_month': selected_month, # None si c'est l'année entière
    }
    return render(request, 'webapp/category_transactions_summary.html', context)


@require_GET
def all_transactions_summary_view(request):
    """
    Vue affichant un récapitulatif de toutes les transactions,
    avec une indication si elles ont été ventilées (ont une allocation).
    """
    # Utilise prefetch_related pour charger les allocations en une seule requête,
    # car 'allocation' est une OneToOneField inversée.
    all_transactions = Transaction.objects.select_related('category', 'account').prefetch_related('allocation').order_by('-date', '-created_at')

    transactions_data = []
    for transaction in all_transactions:
        # Vérifier si la transaction a une allocation associée
        # hasattr(transaction, 'allocation') vérifie l'existence de l'objet lié
        # transaction.allocation est l'objet Allocation ou None si non lié
        is_allocated = hasattr(transaction, 'allocation') and transaction.allocation is not None

        transactions_data.append({
            'id': transaction.id,
            'date': transaction.date,
            'description': transaction.description,
            'amount': transaction.amount,
            'category_name': transaction.category.name if transaction.category else 'N/A',
            'account_name': transaction.account.name,
            'account_currency': transaction.account.currency,
            'transaction_type': transaction.get_transaction_type_display(),
            'is_allocated': is_allocated,
            'account_type': transaction.account.account_type, # Ajoutez le type de compte
        })
    
    context = {
        'page_title': 'Toutes les Transactions',
        'transactions': transactions_data,
    }
    return render(request, 'webapp/all_transactions_summary.html', context)


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
                    # Les tags ne sont pas dans le split form, donc ils ne sont pas passés ici.
                    # Si nécessaire, il faudrait les ajouter au SplitTransactionLineForm.
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


@require_GET
def allocate_income_view(request, transaction_id):
    """
    Vue pour allouer une transaction de revenu (type IN) à différents fonds.
    Cette vue affichera un formulaire pour définir les lignes d'allocation.
    """
    original_transaction = get_object_or_404(Transaction, pk=transaction_id)

    # Vérifier que la transaction est bien un revenu et n'a pas déjà d'allocation
    if original_transaction.transaction_type != 'IN':
        messages.error(request, "Seules les transactions de type 'Revenu' peuvent être allouées.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'allocation'):
        messages.warning(request, f"La transaction '{original_transaction.description}' a déjà été allouée.")
        # Optionnel: Rediriger vers l'édition de l'allocation existante si vous en implémentez une.
        # Pour l'instant, on redirige et on affiche un message.
        return redirect('all_transactions_summary_view')
    
    # Créer une instance vide du formulaire principal d'Allocation
    form = AllocationForm(initial={'notes': f"Allocation pour: {original_transaction.description}"})
    # Créer un formset pour les lignes d'allocation
    # Le formset sera vide par défaut pour permettre à l'utilisateur d'ajouter des lignes.
    formset = AllocationLineFormset()

    # Récupérer toutes les catégories qui gèrent un fonds pour le JS
    fund_managed_categories = []
    for cat in Category.objects.filter(is_fund_managed=True).order_by('name'):
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
        'fund_managed_categories_json': json.dumps(fund_managed_categories), # Pour le JS de la page d'allocation
    }
    return render(request, 'webapp/allocate_income.html', context)


@require_POST
def process_allocation_income(request, transaction_id):
    """
    Gère la soumission du formulaire d'allocation de revenu.
    Crée l'objet Allocation et ses lignes, puis met à jour les fonds.
    """
    original_transaction = get_object_or_404(Transaction, pk=transaction_id)

    if original_transaction.transaction_type != 'IN':
        messages.error(request, "Opération invalide: Seules les transactions de type 'Revenu' peuvent être allouées.")
        return redirect('all_transactions_summary_view')
    if hasattr(original_transaction, 'allocation'):
        messages.error(request, f"Cette transaction a déjà été allouée.")
        return redirect('all_transactions_summary_view')

    form = AllocationForm(request.POST)
    formset = AllocationLineFormset(request.POST)

    if form.is_valid() and formset.is_valid():
        total_allocated_amount = Decimal('0.00')
        lines_to_create = []

        for line_form in formset:
            if not line_form.cleaned_data.get('DELETE', False):
                allocated_amount = line_form.cleaned_data['amount']
                category = line_form.cleaned_data['category']
                notes = line_form.cleaned_data.get('notes', '')

                # Vérifier que la catégorie gère bien un fonds
                if not category.is_fund_managed:
                    messages.error(request, f"La catégorie '{category.name}' ne gère pas de fonds et ne peut pas recevoir d'allocation directe.")
                    # Re-rendre la page avec les erreurs
                    fund_managed_categories = []
                    for cat in Category.objects.filter(is_fund_managed=True).order_by('name'):
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

        # Validation finale : la somme allouée ne doit pas dépasser le montant de la transaction originale
        # Utilisez abs() pour comparer les montants absolus
        if total_allocated_amount > abs(original_transaction.amount) + Decimal('0.01'): # Ajouter une petite tolérance
            messages.error(request, f"Le montant total alloué ({total_allocated_amount:.2f} CHF) dépasse le montant de la transaction originale ({abs(original_transaction.amount):.2f} CHF).")
            # Re-rendre la page avec les erreurs
            fund_managed_categories = []
            for cat in Category.objects.filter(is_fund_managed=True).order_by('name'):
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
        
        # Et si le montant alloué est inférieur, c'est OK, il reste simplement une partie non allouée.
        # if total_allocated_amount < abs(original_transaction.amount) - Decimal('0.01'):
        #     messages.warning(request, f"Le montant total alloué ({total_allocated_amount:.2f} CHF) est inférieur au montant de la transaction originale ({abs(original_transaction.amount):.2f} CHF). Une partie du revenu ne sera pas allouée aux fonds.")


        try:
            with db_transaction.atomic():
                # Créer l'objet Allocation
                allocation = Allocation.objects.create(
                    transaction=original_transaction,
                    total_allocated_amount=total_allocated_amount,
                    notes=form.cleaned_data.get('notes', '')
                )

                # Créer les lignes d'allocation et mettre à jour les fonds
                for line_data in lines_to_create:
                    AllocationLine.objects.create(
                        allocation=allocation,
                        category=line_data['category'],
                        amount=line_data['amount'],
                        notes=line_data['notes']
                    )
                    # Mettre à jour le solde du fonds
                    Fund.objects.add_funds_to_category(line_data['category'], line_data['amount'])
            
            messages.success(request, f"Revenu de {original_transaction.amount:.2f} CHF alloué avec succès aux fonds.")
            return redirect('all_transactions_summary_view')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'allocation du revenu: {e}")
    else:
        messages.error(request, "Veuillez corriger les erreurs dans le formulaire d'allocation.")

    # Si le formulaire n'est pas valide ou s'il y a une erreur, re-rendre la page d'allocation
    fund_managed_categories = []
    for cat in Category.objects.filter(is_fund_managed=True).order_by('name'):
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
