# webapp/admin.py
# Ce fichier enregistre les modèles de l'application dans l'interface d'administration de Django.

from django.contrib import admin
# Importation des modèles depuis le même répertoire (webapp.models)
from .models import Account, Category, Transaction, Budget, SavingGoal, Fund, Tag # Importez le nouveau modèle Tag

# Définir une classe Admin pour la Catégorie pour afficher le nouveau champ
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_fund_managed', 'is_budgeted', 'last_used_at') # Affiche les champs dans la liste d'administration
    list_filter = ('is_fund_managed', 'is_budgeted') # Permet de filtrer par ces champs
    search_fields = ('name', 'description') # Permet de rechercher par nom ou description

# Enregistrement de chaque modèle pour qu'il apparaisse dans l'interface d'administration.
admin.site.register(Account) # modèle de compte
# Enregistrez la Catégorie avec votre classe CategoryAdmin personnalisée
admin.site.register(Category, CategoryAdmin) 
admin.site.register(Transaction) # modèle de transaction
admin.site.register(Budget) # modèle de budget
admin.site.register(SavingGoal) # modèle d'objectif d'épargne
admin.site.register(Fund) #  modèle de fonds budgétaires
admin.site.register(Tag) # le modèle Tag
