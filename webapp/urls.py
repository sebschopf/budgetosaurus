# webapp/urls.py
# Ce fichier définit les chemins d'URL pour les vues de l'application 'webapp'.

from django.urls import path
from . import views # Importe toutes les vues de l'application actuelle

urlpatterns = [
    # URL de la page d'accueil/tableau de bord
    path('', views.dashboard_view, name='dashboard_view'),
    
    # URL pour la soumission du formulaire d'ajout de transaction (POST seulement)
    path('add-transaction-submit/', views.add_transaction_submit, name='add_transaction_submit'),
    
    # URL pour la requête AJAX de chargement des sous-catégories
    path('load-subcategories/', views.load_subcategories, name='load_subcategories'),
    
    # URL pour la page d'importation des catégories via CSV
    path('import-categories/', views.import_categories, name='import_categories'),
    
    # URL pour la page de l'aperçu des budgets
    path('budget-overview/', views.budget_overview, name='budget_overview'),
]

