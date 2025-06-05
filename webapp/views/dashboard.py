# webapp/views/dashboard.py
from django.shortcuts import render
from django.core.serializers import serialize # Importez le module de sérialisation
import json # Importez le module json

from ..services import TransactionService
from ..models import Category # Assurez-vous d'importer Category

def dashboard_view(request):
    """
    Vue principale affichant le tableau de bord : soldes des comptes,
    formulaire d'ajout de transaction et dernières transactions.
    Utilise TransactionService pour la logique métier.
    """
    transaction_service = TransactionService() # Instanciation du service

    account_balances = transaction_service.get_account_balances()
    latest_transactions = transaction_service.get_latest_transactions(limit=10)

    # Préparer une instance du formulaire de transaction
    from ..forms import TransactionForm
    form = TransactionForm()

    # Récupérer toutes les catégories pour le JS, incluant l'info is_fund_managed
    # et gérer la structure parent/enfant.
    # Pour le JS, nous voulons une liste simple de catégories et de sous-catégories
    # avec leurs IDs, noms et statut 'is_fund_managed'.
    all_categories_data = []
    all_subcategories_data = []

    # Catégories de niveau supérieur (parents)
    for cat in Category.objects.filter(parent__isnull=True).order_by('name'):
        all_categories_data.append({
            'id': cat.id,
            'name': cat.name,
            'is_fund_managed': cat.is_fund_managed
        })
        # Sous-catégories associées (enfants)
        for child_cat in cat.children.all().order_by('name'):
            all_subcategories_data.append({
                'id': child_cat.id,
                'name': child_cat.name,
                'parent': cat.id,
                'is_fund_managed': child_cat.is_fund_managed
            })
    
    # Convertir les listes Python en chaînes JSON
    all_categories_data_json = json.dumps(all_categories_data)
    all_subcategories_data_json = json.dumps(all_subcategories_data)


    context = {
        'page_title': 'Tableau de Bord',
        'account_balances': account_balances,
        'transactions': latest_transactions,
        'form': form, # Le formulaire est inclus pour être affiché dans le template
        'all_categories_data_json': all_categories_data_json, # Données des catégories pour le JS
        'all_subcategories_data_json': all_subcategories_data_json, # Données des sous-catégories pour le JS
    }
    return render(request, 'webapp/index.html', context)


def recap_overview_view(request):
    """
    Vue pour la page d'aperçu des différents récapitulatifs et outils de gestion.
    Sert de hub pour les vues de transactions détaillées et de division.
    """
    context = {
        'page_title': 'Vos Récapitulatifs et Outils',
    }
    return render(request, 'webapp/recap_overview.html', context)

