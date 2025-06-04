# webapp/views.py
# Ce fichier contient les vues (fonctions de gestion des requêtes HTTP) de l'application.

import csv
import io
from datetime import date
import calendar # Pour obtenir le nom des mois

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages # Pour afficher des messages de feedback à l'utilisateur
from django.db.models import Sum, F # Pour les agrégations de base de données
from django.db import transaction as db_transaction # Pour gérer les transactions atomiques

# Importation des modèles et formulaires depuis le même répertoire (webapp)
from .models import Transaction, Category, Account, Budget, SavingGoal
from .forms import TransactionForm, CategoryImportForm


def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    """
    # Récupérer tous les comptes et calculer leurs soldes actuels
    accounts = Account.objects.all().order_by('name')
    account_balances = {}
    for account in accounts:
        # Calcul des revenus et dépenses pour ce compte
        total_income = account.transactions.filter(transaction_type='IN').aggregate(Sum('amount'))['amount__sum'] or 0
        total_expense = account.transactions.filter(transaction_type='OUT').aggregate(Sum('amount'))['amount__sum'] or 0
        
        # Le solde actuel est le solde initial + revenus - dépenses
        # (Les dépenses sont stockées comme des nombres négatifs, donc l'addition fonctionne)
        balance = account.initial_balance + total_income + total_expense
        account_balances[account.name] = {
            'balance': balance,
            'currency': account.currency
        }

    # Récupérer les 10 dernières transactions pour l'affichage
    # select_related() optimise les requêtes en joignant les données de Category et Account
    latest_transactions = Transaction.objects.all().select_related('category', 'account').order_by('-date', '-created_at')[:10]

    # Préparer une instance du formulaire de transaction
    form = TransactionForm()

    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances,
        'transactions': latest_transactions,
        'form': form, # Le formulaire est inclus pour être affiché dans le template
    }
    return render(request, 'webapp/index.html', context)


@require_POST # Cette vue ne doit répondre qu'aux requêtes POST (soumission de formulaire)
def add_transaction_submit(request):
    """
    Gère la soumission du formulaire d'ajout de transaction depuis le tableau de bord.
    """
    form = TransactionForm(request.POST)
    if form.is_valid():
        form.save()
        messages.success(request, "Transaction enregistrée avec succès!")
        return redirect('dashboard_view') # Redirige vers le tableau de bord après une soumission réussie
    else:
        # Si le formulaire n'est pas valide, afficher les erreurs et re-rendre le tableau de bord
        messages.error(request, "Erreur lors de l'enregistrement de la transaction. Veuillez corriger les erreurs.")
        
        # Re-calculer les données nécessaires pour le tableau de bord pour les re-afficher
        accounts = Account.objects.all().order_by('name')
        account_balances = {}
        for account in accounts:
            balance = account.initial_balance + (account.transactions.aggregate(Sum('amount'))['amount__sum'] or 0)
            account_balances[account.name] = {
                'balance': balance,
                'currency': account.currency
            }
        latest_transactions = Transaction.objects.all().select_related('category', 'account').order_by('-date', '-created_at')[:10]
        
        context = {
            'page_title': 'Tableau de Bord',
            'account_balances': account_balances,
            'transactions': latest_transactions,
            'form': form, # Le formulaire avec les erreurs est passé au template
        }
        return render(request, 'webapp/index.html', context)


@require_GET # Cette vue ne doit répondre qu'aux requêtes GET (requêtes AJAX)
def load_subcategories(request):
    """
    Vue AJAX pour charger les sous-catégories en fonction d'une catégorie parente sélectionnée.
    """
    parent_id = request.GET.get('parent_category_id')
    subcategories = []
    if parent_id:
        try:
            parent_category = Category.objects.get(pk=parent_id)
            # Récupère tous les enfants (sous-catégories) de la catégorie parente
            children = parent_category.children.all().order_by('name')
            for child in children:
                subcategories.append({'id': child.id, 'name': child.name})
        except Category.DoesNotExist:
            # Si l'ID de la catégorie parente n'existe pas, retourne une liste vide
            pass
    # Retourne la liste des sous-catégories au format JSON
    return JsonResponse(subcategories, safe=False)


def import_categories(request):
    """
    Vue pour importer des catégories à partir d'un fichier CSV.
    Le CSV doit avoir les colonnes 'name' et 'parent_name' (optionnel).
    """
    if request.method == 'POST':
        form = CategoryImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            # Lire le contenu du fichier CSV en mémoire
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            imported_count = 0
            updated_count = 0
            errors = []

            # Utilise une transaction atomique pour garantir que toutes les opérations
            # sont validées ou annulées ensemble en cas d'erreur.
            with db_transaction.atomic():
                for row in reader:
                    try:
                        category_name = row.get('name')
                        parent_name = row.get('parent_name')

                        if not category_name:
                            errors.append(f"Ligne ignorée (vide ou 'name' manquant) à la ligne {reader.line_num}.")
                            continue

                        # Récupère ou crée la catégorie actuelle
                        category, created = Category.objects.get_or_create(name=category_name)
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1

                        # Si un nom de parent est fourni, récupère ou crée le parent et l'assigne
                        if parent_name:
                            parent_category, parent_created = Category.objects.get_or_create(name=parent_name)
                            if category.parent != parent_category: # Met à jour le parent seulement si différent
                                category.parent = parent_category
                                category.save()

                    except Exception as e:
                        # Capture les erreurs spécifiques à une ligne et les stocke
                        errors.append(f"Erreur à la ligne {reader.line_num} ({row.get('name', 'N/A')}): {e}")
                        # Si vous voulez annuler toute la transaction en cas de la première erreur, décommentez 'raise e'
                        # raise e

            if not errors:
                messages.success(request, f"Importation réussie : {imported_count} nouvelles catégories, {updated_count} catégories existantes mises à jour.")
            else:
                messages.warning(request, f"Importation terminée avec des erreurs. {imported_count} nouvelles, {updated_count} mises à jour. Erreurs: {', '.join(errors[:5])}...") # Affiche les 5 premières erreurs
            return redirect('import_categories') # Redirige vers la page d'importation
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire de téléchargement.")
    else:
        form = CategoryImportForm() # Formulaire vide pour une requête GET

    return render(request, 'webapp/import_categories.html', {'form': form})


def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours.
    """
    current_month = date.today().month
    current_year = date.today().year

    # Récupérer les budgets mensuels configurés pour le mois et l'année en cours
    budgets = Budget.objects.filter(
        period_type='M', # Filtrer pour les budgets mensuels
        start_date__month=current_month,
        start_date__year=current_year
    ).select_related('category') # Optimiser la requête pour récupérer la catégorie associée

    budget_data = []
    for budget in budgets:
        # Calculer les dépenses réelles pour cette catégorie et ses sous-catégories pour le mois
        # Inclut l'ID de la catégorie parente et de tous ses enfants
        category_and_children_ids = [budget.category.id] + list(budget.category.children.values_list('id', flat=True))
        
        spent_amount = Transaction.objects.filter(
            category__id__in=category_and_children_ids, # Filtrer par la catégorie et ses sous-catégories
            transaction_type='OUT', # Seules les dépenses
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        # Les montants de dépenses sont stockés comme négatifs, donc on prend la valeur absolue pour l'affichage
        spent_amount = abs(spent_amount)

        remaining = budget.amount - spent_amount
        # Calcul du pourcentage dépensé (évite la division par zéro si le budget est 0)
        percentage_spent = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0

        budget_data.append({
            'category_name': budget.category.name,
            'budgeted_amount': budget.amount,
            'spent_amount': spent_amount,
            'remaining': remaining,
            'percentage_spent': round(percentage_spent, 2), # Arrondi à 2 décimales
            'status': 'ok' if remaining >= 0 else 'overbudget' # Statut visuel
        })
    
    # Calculer le total des revenus et dépenses pour le mois en cours
    total_income_month = Transaction.objects.filter(
        transaction_type='IN',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_expense_month = Transaction.objects.filter(
        transaction_type='OUT',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense_month = abs(total_expense_month) # Prendre l'absolu pour l'affichage

    context = {
        'page_title': 'Aperçu des Budgets',
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'budget_data': budget_data,
        'total_income_month': total_income_month,
        'total_expense_month': total_expense_month,
    }
    return render(request, 'webapp/budget_overview.html', context)

