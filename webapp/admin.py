# webapp/admin.py
# Ce fichier enregistre les modèles de l'application dans l'interface d'administration de Django.

from django.contrib import admin
from django.contrib import messages # Importez messages pour les messages de succès
from django.db import transaction as db_transaction # Pour les opérations atomiques

# Importation des modèles depuis le même répertoire (webapp.models)
from .models import (
    Account, Category, Transaction, Budget, SavingGoal, Fund, Tag,
    Allocation, AllocationLine,
    FundDebitRecord, FundDebitLine
)

# Définir une classe Admin pour la Catégorie pour afficher le nouveau champ
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_fund_managed', 'is_budgeted', 'last_used_at')
    list_filter = ('is_fund_managed', 'is_budgeted')
    search_fields = ('name', 'description')

# Classes Inline pour AllocationLine et FundDebitLine
class AllocationLineInline(admin.TabularInline):
    model = AllocationLine
    extra = 1
    fields = ['category', 'amount', 'notes']

class FundDebitLineInline(admin.TabularInline):
    model = FundDebitLine
    extra = 1
    fields = ['category', 'amount', 'notes']

# Classes Admin pour Allocation et FundDebitRecord avec leurs Inlines
class AllocationAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'total_allocated_amount', 'notes', 'created_at')
    inlines = [AllocationLineInline]
    search_fields = ('transaction__description', 'notes')

class FundDebitRecordAdmin(admin.ModelAdmin):
    list_display = ('transaction', 'total_debited_amount', 'notes', 'created_at')
    inlines = [FundDebitLineInline]
    search_fields = ('transaction__description', 'notes')

#  Classes Admin améliorées pour d'autres modèles

class AccountAdmin(admin.ModelAdmin):
    """
    Personnalisation de l'administration pour le modèle Account.
    """
    list_display = ('name', 'currency', 'initial_balance', 'account_type')
    list_filter = ('account_type', 'currency')
    search_fields = ('name',)

class TransactionAdmin(admin.ModelAdmin):
    """
    Personnalisation de l'administration pour le modèle Transaction.
    """
    list_display = ('date', 'description', 'amount', 'category', 'account', 'transaction_type', 'display_tags', 'created_at')
    list_filter = ('transaction_type', 'account', 'category', 'date')
    search_fields = ('description',)
    date_hierarchy = 'date' # Ajoute une navigation par date
    raw_id_fields = ('account', 'category') # Utile beaucoup de comptes/catégories pour les sélecteurs

    def display_tags(self, obj):
        """Affiche les tags associés à la transaction."""
        return ", ".join([tag.name for tag in obj.tags.all()])
    display_tags.short_description = "Tags" # Nom de la colonne dans list_display

    # Actions personnalisées
    actions = ['mark_transactions_as_reviewed']

    def mark_transactions_as_reviewed(self, request, queryset):
        """
        Action d'administration pour marquer les transactions sélectionnées comme "révisées".
        Cela leur assigne une catégorie par défaut ('Non Catégorisé' ou 'Divers')
        si elles n'en ont pas, les retirant ainsi de la vue "Transactions à Revoir".
        """
        # Obtenir ou créer une catégorie par défaut pour les transactions non catégorisées.
        # Vous pouvez la renommer ou la modifier selon vos préférences.
        default_category, created = Category.objects.get_or_create(
            name="Non Catégorisé",
            defaults={'description': "Catégorie par défaut pour les transactions révisées sans attribution spécifique."}
        )

        updated_count = 0
        with db_transaction.atomic(): # Assure l'atomicité de l'opération
            for transaction in queryset:
                if transaction.category is None: # Ne modifie que les transactions sans catégorie
                    transaction.category = default_category
                    transaction.save() # La sauvegarde déclenchera aussi le signal de normalisation du montant
                    updated_count += 1

        if updated_count == 1:
            message_bit = "1 transaction a été marquée"
        else:
            message_bit = f"{updated_count} transactions ont été marquées"
        
        self.message_user(request, f"{message_bit} comme révisée(s) et catégorisée(s) en '{default_category.name}'.", messages.SUCCESS)

    mark_transactions_as_reviewed.short_description = "Marquer les transactions sélectionnées comme révisées" # Nom affiché dans le menu déroulant des actions

class BudgetAdmin(admin.ModelAdmin):
    """
    Personnalisation de l'administration pour le modèle Budget.
    """
    list_display = ('category', 'amount', 'period_type', 'start_date', 'end_date')
    list_filter = ('period_type', 'category')
    search_fields = ('category__name',) # Permet de rechercher par le nom de la catégorie

class SavingGoalAdmin(admin.ModelAdmin):
    """
    Personnalisation de l'administration pour le modèle SavingGoal.
    """
    list_display = ('name', 'target_amount', 'current_amount_saved', 'target_date', 'status', 'category')
    list_filter = ('status', 'target_date', 'category')
    search_fields = ('name', 'notes', 'category__name')

class FundAdmin(admin.ModelAdmin):
    """
    Personnalisation de l'administration pour le modèle Fund.
    """
    list_display = ('category', 'current_balance', 'last_updated')
    list_filter = ('category',)
    search_fields = ('category__name',)


# Enregistrement de chaque modèle pour qu'il apparaisse dans l'interface d'administration.
admin.site.register(Account, AccountAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(Budget, BudgetAdmin)
admin.site.register(SavingGoal, SavingGoalAdmin)
admin.site.register(Fund, FundAdmin)
admin.site.register(Tag) # Le modèle Tag est simple.

admin.site.register(Allocation, AllocationAdmin)
admin.site.register(AllocationLine)
admin.site.register(FundDebitRecord, FundDebitRecordAdmin)
admin.site.register(FundDebitLine)
