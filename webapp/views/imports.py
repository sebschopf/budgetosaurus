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

from ..models import Category, Budget, Transaction
# Importe les importateurs depuis le nouveau paquet 'importers'
from ..importers import (
    CsvTransactionImporter,
    RaiffeisenCsvTransactionImporter,
    XmlIsoTransactionImporter,
    SwiftMt940TransactionImporter
)
from ..forms import CategoryImportForm, TransactionImportForm
from ..services import TransactionImportService


def import_categories(request):
    """
    Vue pour importer des catégories à partir d'un fichier CSV.
    Le CSV doit avoir les colonnes 'name' et 'parent_name' (optionnel).
    """
    if request.method == 'POST':
        form = CategoryImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['csv_file']
            # Essayer de décoder avec 'utf-8', puis 'latin-1' si 'utf-8' échoue
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

                        category, created = Category.objects.get_or_create(name=category_name)
                        if created:
                            imported_count += 1
                        else:
                            updated_count += 1

                        if parent_name:
                            parent_category, parent_created = Category.objects.get_or_create(name=parent_name)
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

    return render(request, 'webapp/import_categories.html', {'form': form})


def import_transactions_view(request):
    """
    Vue pour importer des transactions à partir d'un fichier.
    Permet à l'utilisateur de choisir le format du fichier et, si nécessaire, de mapper les colonnes.
    """
    if request.method == 'POST':
        form = TransactionImportForm(request.POST, request.FILES)
        if form.is_valid():
            file_to_import = form.cleaned_data['csv_file']
            account = form.cleaned_data['account']
            importer_type = form.cleaned_data['importer_type']
            
            importer = None
            column_mapping = None

            if importer_type == 'generic_csv':
                column_mapping = {
                    'date': form.cleaned_data['date_column'],
                    'description': form.cleaned_data['description_column'],
                    'amount': form.cleaned_data['amount_column'],
                }
                importer = CsvTransactionImporter()
            elif importer_type == 'raiffeisen_csv':
                importer = RaiffeisenCsvTransactionImporter()
            elif importer_type == 'xml_iso':
                importer = XmlIsoTransactionImporter()
            elif importer_type == 'swift_mt940':
                importer = SwiftMt940TransactionImporter()
            else:
                messages.error(request, "Type d'importateur non valide.")
                return redirect('import_transactions_view')

            if importer is None:
                messages.error(request, "Impossible de déterminer l'importateur pour le type de fichier sélectionné.")
                return redirect('import_transactions_view')

            # Lire le contenu du fichier
            try:
                # La méthode .read() lit le fichier entier, .decode() le convertit en string
                # Il est important de réinitialiser le curseur du fichier si vous lisez plusieurs fois
                # ou si le fichier est déjà lu (ex: par form.cleaned_data)
                # Pour les fichiers téléchargés, .read() est généralement suffisant une fois.
                file_to_import.seek(0) # S'assurer que le curseur est au début du fichier
                file_content = file_to_import.read().decode('utf-8')
            except UnicodeDecodeError:
                file_to_import.seek(0) # Réinitialiser avant de réessayer
                file_content = file_to_import.read().decode('latin-1')
            
            importer_service = TransactionImportService(importer)
            
            try:
                imported_count = importer_service.process_import(file_content, account, column_mapping)
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
        form = TransactionImportForm()

    context = {
        'page_title': 'Importer des Transactions',
        'form': form,
    }
    return render(request, 'webapp/import_transactions.html', context)


def budget_overview(request):
    """
    Vue affichant un aperçu des budgets et un résumé des revenus/dépenses pour le mois en cours.
    """
    current_month = date.today().month
    current_year = date.today().year

    budgets = Budget.objects.filter(
        period_type='M',
        start_date__month=current_month,
        start_date__year=current_year
    ).select_related('category')

    budget_data = []
    for budget in budgets:
        category_and_children_ids = [budget.category.id] + list(budget.category.children.values_list('id', flat=True))
        
        spent_amount = Transaction.objects.filter(
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
