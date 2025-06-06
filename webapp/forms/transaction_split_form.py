# webapp/forms/transaction_split_form.py
from django import forms
from django.forms import formset_factory
from ..models import Category, Transaction

class SplitTransactionLineForm(forms.Form):
    """
    Formulaire pour une seule ligne de division d'une transaction.
    """
    description = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'placeholder': 'Description', 'class': 'p-2 border rounded-md w-full'})
    )
    amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Montant', 'class': 'p-2 border rounded-md w-full'})
    )
    # Champ pour la catégorie principale (sans parent)
    main_category = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True).order_by('name'),
        empty_label="Sélectionner Catégorie Principale",
        required=True, # Rendre obligatoire au niveau du formulaire
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full split-category-main'})
    )
    # Champ pour la sous-catégorie (initialement vide, rempli par JS)
    subcategory = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Sera peuplé par JS en fonction de main_category
        empty_label="Sélectionner Sous-catégorie",
        required=False, # Pas obligatoire si la catégorie principale est suffisante
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full split-category subcategory-hidden'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si le formulaire est pré-rempli (par exemple, après une erreur de soumission)
        # Ou si nous voulons initialiser les sous-catégories pour une ligne existante
        if self.is_bound or self.initial:
            # Récupérer la catégorie principale soumise pour cette ligne spécifique du formset
            # self.prefix est crucial pour accéder aux données du formset
            main_category_id = self.data.get(f'{self.prefix}-main_category') if self.is_bound else self.initial.get('main_category')
            if main_category_id:
                try:
                    main_category_instance = Category.objects.get(pk=main_category_id)
                    self.fields['subcategory'].queryset = main_category_instance.children.all().order_by('name')
                except Category.DoesNotExist:
                    self.fields['subcategory'].queryset = Category.objects.none()

    def clean(self):
        """
        Validation personnalisée pour s'assurer qu'une catégorie finale est sélectionnée
        et que la sous-catégorie, si présente, appartient bien à la catégorie principale.
        """
        cleaned_data = super().clean()
        
        main_category = cleaned_data.get('main_category')
        subcategory = cleaned_data.get('subcategory')

        # Initialiser final_category à None pour s'assurer que la clé existe toujours
        final_category_object = None 

        if main_category: # Traiter la logique seulement si une catégorie principale est sélectionnée
            if subcategory:
                # Si une sous-catégorie est sélectionnée, s'assurer qu'elle appartient à la catégorie principale
                if subcategory.parent != main_category:
                    self.add_error('subcategory', "Cette sous-catégorie n'appartient pas à la catégorie principale sélectionnée.")
                final_category_object = subcategory
            else:
                # Si seule la catégorie principale est sélectionnée, c'est elle la catégorie finale.
                final_category_object = main_category
        else:
            # Si aucune catégorie principale n'est sélectionnée (malgré required=True sur le champ ModelChoiceField),
            # nous ajoutons explicitement une erreur pour garantir la validation.
            # Le message par défaut "This field is required" devrait déjà apparaître, mais ceci renforce.
            if not self.errors.get('main_category'): # Évite de dupliquer les messages d'erreur
                self.add_error('main_category', "Veuillez sélectionner une catégorie principale.")
            
        # Assurez-vous que 'final_category' est toujours ajouté à cleaned_data, même si final_category_object est None
        cleaned_data['final_category'] = final_category_object 
        
        return cleaned_data

# Création du formset pour gérer plusieurs instances de SplitTransactionLineForm
# extra=1 signifie qu'une ligne vide sera affichée par défaut en plus des données initiales.
# can_delete=True ajoute une case à cocher 'delete' pour supprimer des lignes.
SplitTransactionFormset = formset_factory(SplitTransactionLineForm, extra=1, can_delete=True)
