# webapp/admin.py
# Ce fichier enregistre les modèles de l'application dans l'interface d'administration de Django.

from django.contrib import admin
# Importation des modèles depuis le même répertoire (webapp.models)
from .models import Account, Category, Transaction, Budget, SavingGoal

# Enregistrement de chaque modèle pour qu'il apparaisse dans l'interface d'administration.
admin.site.register(Account)
admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(Budget)
admin.site.register(SavingGoal)