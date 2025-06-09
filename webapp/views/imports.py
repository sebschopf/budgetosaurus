# webapp/views/imports.py
import csv
import io
from datetime import date
import calendar

from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.db import transaction as db_transaction
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
from ..models import Category, Budget, Transaction
from ..importers import (
    CsvTransactionImporter,
    RaiffeisenCsvTransactionImporter,
    XmlIsoTransactionImporter,
    SwiftMt940TransactionImporter
)
from ..forms import CategoryImportForm, TransactionImportForm
from ..services import TransactionImportService


@login_required
def import_categories(request):
    """
    Vue pour importer des catégories à partir d'un fichier CSV pour l'utilisateur connecté.
    Le CSV doit avoir les colonnes 'name' et 'parent_name' (optionnel).
    """
    if request.method == 'POST':
        # Passer l'utilisateur au formulaire pour filtrer les choix si nécessaire (pas de ModelChoiceField ici)
        form = CategoryImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            try:
                decoded_file = csv_file.read().decode('utf-8')
            except UnicodeDecodeError:
                decoded_file = csv_file.read().decode('latin-1')

            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            imported_count = 0
            updated_count = 0
            errors = []

            with db_transaction.atomic():
                for row in reader:
                    try:
                        category_name = row.get('name')
                        parent_name = row.get('parent_name')

                        if not category_name:
                            errors.append(f"Ligne ignorée (vide ou 'name' manquant) à la ligne {reader.line_num}.")
                            continue

                        # Assigner la catégorie à l'utilisateur
                        category, created = Category.objects.get_or_create(user=request.user, name=category_name)
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1

                        if parent_name:
                            # Assigner le parent à l'utilisateur
                            parent_category, parent_created = Category.objects.get_or_create(user=request.user, name=parent_name)
                            if category.parent != parent_category:
                                category.parent = parent_category
                                category.save()

                    except Exception as e:
                        errors.append(f"Erreur à la ligne {reader.line_num} ({row.get('name', 'N/A')}): {e}")

            if not errors:
                messages.success(request, f"Importation réussie : {imported_count} nouvelles catégories, {updated_count} catégories existantes mises à jour.")
            else:
                messages.warning(request, f"Importation terminée avec des erreurs. {imported_count} nouvelles, {updated_count} mises à jour. Erreurs: {', '.join(errors[:5])}...")
            return redirect('import_categories')
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire de téléchargement.")
    else:
        form = CategoryImportForm()

    context = {
        'page_title': 'Importer des Catégories', 
        'form': form,
    }
    return render(request, 'webapp/import_categories.html', context)


@login_required 
def import_transactions_view(request):
    """
    Vue pour importer des transactions à partir d'un fichier pour l'utilisateur connecté.
    Permet à l'utilisateur de choisir le format du fichier et, si nécessaire, de mapper les colonnes.
    """
    if request.method == 'POST':
        # Passer l'utilisateur au formulaire pour filtrer les choix de compte
        form = TransactionImportForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            file_to_import = form.cleaned_data['csv_file']
            account = form.cleaned_data['account']
            importer_type = form.cleaned_data['importer_type']

            importer_instance = None # Renommé pour éviter le conflit avec la classe Importer
            column_mapping = None

            if importer_type == 'generic_csv':
                column_mapping = {
                    'date': form.cleaned_data['date_column'],
                    'description': form.cleaned_data['description_column'],
                    'amount': form.cleaned_data['amount_column'],
                }
                importer_instance = CsvTransactionImporter()
            elif importer_type == 'raiffeisen_csv':
                importer_instance = RaiffeisenCsvTransactionImporter()
            elif importer_type == 'xml_iso':
                importer_instance = XmlIsoTransactionImporter()
            elif importer_type == 'swift_mt940':
                importer_instance = SwiftMt940TransactionImporter()
            else:
                messages.error(request, "Type d'importateur non valide.")
                return redirect('import_transactions_view')

            if importer_instance is None:
                messages.error(request, "Impossible de déterminer l'importateur pour le type de fichier sélectionné.")
                return redirect('import_transactions_view')

            try:
                file_to_import.seek(0)
                file_content = file_to_import.read().decode('utf-8')
            except UnicodeDecodeError:
                file_to_import.seek(0)
                file_content = file_to_import.read().decode('latin-1')

            # Instancier le service d'importation sans l'importer, car il est passé à process_import
            importer_service = TransactionImportService()

            try:
                # Passer l'utilisateur et l'instance de l'importer au service
                imported_count = importer_service.process_import(file_content, account, request.user, importer_instance, column_mapping)
                messages.success(request, f"{imported_count} transactions importées avec succès pour le compte '{account.name}'.")
                return redirect('dashboard_view')
            except NotImplementedError as e:
                messages.error(request, f"Fonctionnalité non implémentée: {e}")
            except ValueError as e:
                messages.error(request, f"Erreur de format de fichier ou de mappage: {e}")
            except Exception as e:
                messages.error(request, f"Une erreur inattendue est survenue lors de l'importation: {e}")
        else:
            messages.error(request, "Veuillez corriger les erreurs dans le formulaire de téléchargement.")
    else:
        # Passer l'utilisateur au formulaire pour filtrer les choix de compte
        form = TransactionImportForm(user=request.user)

    context = {
        'page_title': 'Importer des Transactions',
        'form': form,
    }
    return render(request, 'webapp/import_transactions.html', context)


@login_required 
def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours
    pour l'utilisateur connecté.
    """
    current_month = date.today().month
    current_year = date.today().year

    # Filtrer les budgets par l'utilisateur
    budgets = Budget.objects.filter(
        user=request.user, # NOUVEAU
        period_type='M',
        start_date__month=current_month,
        start_date__year=current_year
    ).select_related('category')

    budget_data = []
    for budget in budgets:
        # Filtrer les catégories et leurs enfants par l'utilisateur
        category_and_children_ids = [budget.category.id] + list(budget.category.children.filter(user=request.user).values_list('id', flat=True)) # NOUVEAU

        # Filtrer les transactions par l'utilisateur
        spent_amount = Transaction.objects.filter(
            user=request.user, # NOUVEAU
            category__id__in=category_and_children_ids,
            transaction_type='OUT',
            date__month=current_month,
            date__year=current_year
        ).aggregate(Sum('amount'))['amount__sum'] or 0

        spent_amount = abs(spent_amount)

        remaining = budget.amount - spent_amount
        percentage_spent = (spent_amount / budget.amount * 100) if budget.amount > 0 else 0

        budget_data.append({
            'category_name': budget.category.name,
            'budgeted_amount': budget.amount,
            'spent_amount': spent_amount,
            'remaining': remaining,
            'percentage_spent': round(percentage_spent, 2),
            'status': 'ok' if remaining >= 0 else 'overbudget'
        })

    # Filtrer les revenus et dépenses par l'utilisateur
    total_income_month = Transaction.objects.filter(
        user=request.user,
        transaction_type='IN',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_expense_month = Transaction.objects.filter(
        user=request.user,
        transaction_type='OUT',
        date__month=current_month,
        date__year=current_year
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense_month = abs(total_expense_month)

    context = {
        'page_title': 'Aperçu des Budgets',
        'current_month_name': calendar.month_name[current_month],
        'current_year': current_year,
        'budget_data': budget_data,
        'total_income_month': total_income_month,
        'total_expense_month': total_expense_month,
    }
    return render(request, 'webapp/budget_overview.html', context)
