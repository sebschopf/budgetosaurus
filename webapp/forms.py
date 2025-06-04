# webapp/forms.py
# Ce fichier contient les définitions des formulaires Django pour l'application.

from django import forms
# Importation des modèles depuis le même répertoire (webapp.models)
from .models import Transaction, Category, Account

class TransactionForm(forms.ModelForm):
    """
    Formulaire pour ajouter et modifier des transactions, avec des listes déroulantes
    dynamiques pour les catégories et sous-catégories.
    """
    # Champ pour la catégorie parente (niveau supérieur)
    # Le queryset est filtré pour n'afficher que les catégories sans parent.
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True).order_by('name'),
        empty_label="Sélectionner une catégorie parente",
        required=False, # La validation finale sera faite dans clean()
        label="Catégorie Principale"
    )

    # Champ pour la sous-catégorie
    # Ce champ est initialement vide et sera rempli dynamiquement par JavaScript.
    subcategory = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ
        empty_label="Sélectionner une sous-catégorie",
        required=False, # La validation finale sera faite dans clean()
        label="Sous-catégorie"
    )

    class Meta:
        model = Transaction
        # Les champs 'category' et 'subcategory' sont gérés explicitement ci-dessus.
        # Le champ 'category' du modèle sera rempli par la logique du formulaire.
        fields = ['date', 'description', 'amount', 'category', 'subcategory', 'account', 'transaction_type']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'p-2 border rounded-md w-full'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'p-2 border rounded-md w-full'}),
            'description': forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full'}),
            'account': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
            'transaction_type': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Initialise le formulaire. Personnalise les querysets et les valeurs initiales
        pour l'édition de transactions.
        """
        super().__init__(*args, **kwargs)

        # Assurer que le queryset du compte est trié
        self.fields['account'].queryset = Account.objects.all().order_by('name')

        # Logique pour pré-remplir les champs en mode édition (si une instance est fournie)
        if self.instance.pk:
            if self.instance.category:
                # Si la catégorie de la transaction a un parent, c'est une sous-catégorie
                if self.instance.category.parent:
                    self.fields['category'].initial = self.instance.category.parent # Définit le parent
                    self.fields['subcategory'].initial = self.instance.category # Définit la sous-catégorie
                    # Remplit le queryset de la sous-catégorie avec les enfants du parent sélectionné
                    self.fields['subcategory'].queryset = self.instance.category.parent.children.all().order_by('name')
                else:
                    # Si la catégorie de la transaction n'a pas de parent, c'est une catégorie de niveau supérieur
                    self.fields['category'].initial = self.instance.category

        # Applique des classes Tailwind CSS à tous les champs du formulaire
        for field_name, field in self.fields.items():
            # Évite de réappliquer des classes si un widget personnalisé est déjà défini
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({'class': 'p-2 border rounded-md w-full'})

    def clean(self):
        """
        Valide les données du formulaire et assigne la catégorie finale à la transaction.
        Gère la logique entre catégorie principale et sous-catégorie.
        """
        cleaned_data = super().clean()
        main_category = cleaned_data.get('category')
        sub_category = cleaned_data.get('subcategory')

        # Validation : Au moins une catégorie (principale ou sous-catégorie) doit être sélectionnée
        if not main_category and not sub_category:
            raise forms.ValidationError("Veuillez sélectionner une catégorie ou une sous-catégorie.")

        # Validation : Si une sous-catégorie est choisie, elle doit appartenir à la catégorie principale sélectionnée
        if sub_category and sub_category.parent != main_category:
            # Si une catégorie principale est sélectionnée, mais la sous-catégorie ne correspond pas
            if main_category:
                raise forms.ValidationError("La sous-catégorie sélectionnée n'appartient pas à la catégorie principale.")
            else:
                # Si une sous-catégorie est sélectionnée sans catégorie principale, on l'assigne directement.
                # Cela suppose que la sous-catégorie est la catégorie la plus spécifique à enregistrer.
                cleaned_data['category'] = sub_category
                return cleaned_data # Retourne les données nettoyées

        # Si une sous-catégorie est sélectionnée, c'est elle qui sera la catégorie finale de la transaction.
        # Sinon, la catégorie principale est déjà dans cleaned_data['category'] et sera utilisée.
        if sub_category:
            cleaned_data['category'] = sub_category
        
        return cleaned_data

class CategoryImportForm(forms.Form):
    """
    Formulaire pour télécharger un fichier CSV afin d'importer des catégories.
    """
    csv_file = forms.FileField(
        label="Fichier CSV de catégories",
        help_text="Téléchargez un fichier CSV avec les colonnes 'name' et 'parent_name' (optionnel).",
        widget=forms.ClearableFileInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )

