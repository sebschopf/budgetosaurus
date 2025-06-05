# webapp/admin.py
# Ce fichier enregistre les modèles de l'application dans l'interface d'administration de Django.

from django.contrib import admin
# Importation des modèles depuis le même répertoire (webapp.models)
from .models import Account, Category, Transaction, Budget, SavingGoal, Fund, Tag # Importez le nouveau modèle Tag

# Enregistrement de chaque modèle pour qu'il apparaisse dans l'interface d'administration.
admin.site.register(Account) # modèle de compte
admin.site.register(Category) # modèle de catégorie
admin.site.register(Transaction) # modèle de transaction
admin.site.register(Budget) # modèle de budget
admin.site.register(SavingGoal) # modèle d'objectif d'épargne
admin.site.register(Fund) #  modèle de fonds budgétaires
admin.site.register(Tag) # le modèle Tag
