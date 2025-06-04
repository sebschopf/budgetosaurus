# core/admin.py

from django.contrib import admin

# Importation des modèles localement à l'intérieur de la fonction si nécessaire,
# mais pour admin.site.register, ils sont généralement accessibles globalement
# une fois que l'AppConfig a fait son travail.

from .models import Account, Category, Transaction, Budget, SavingGoal
admin.site.register(Account)
admin.site.register(Category)
admin.site.register(Transaction)
admin.site.register(Budget)
admin.site.register(SavingGoal)

