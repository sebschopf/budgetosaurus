# webapp/forms/transaction_form.py
from django import forms
from ..models import Transaction, Category, Account, Tag # Importation des modèles Tag
from django.db.models import Q # Importation de Q pour les requêtes complexes

class TransactionForm(forms.ModelForm):
    """
    Formulaire pour ajouter et modifier des transactions, avec des listes déroulantes
    dynamiques pour les catégories et sous-catégories, et un champ pour les tags.
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

    # Nouveau champ pour les tags
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'), # Affiche tous les tags disponibles
        widget=forms.CheckboxSelectMultiple, # Permet de sélectionner plusieurs tags via des cases à cocher
        required=False,
        label="Tags"
    )

    class Meta:
        model = Transaction
        # Les champs 'category' et 'subcategory' sont gérés explicitement ci-dessus.
        # Le champ 'category' du modèle sera rempli par la logique du formulaire.
        fields = ['date', 'description', 'amount', 'category', 'subcategory', 'account', 'transaction_type', 'tags'] # Ajout de 'tags'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'p-2 border rounded-md w-full'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'p-2 border rounded-md w-full'}),
            'description': forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full', 'list': 'commonDescriptionsList'}), # Ajout de list pour l'autocomplétion
            'account': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
            'transaction_type': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
            # 'tags': forms.CheckboxSelectMultiple n'est pas mis ici car il est déjà défini dans le champ 'tags'
        }

    def __init__(self, *args, **kwargs):
        """
        Initialise le formulaire. Personnalise les querysets et les valeurs initiales
        pour l'édition de transactions, et assure la population correcte des sous-catégories
        lors de la re-soumission du formulaire.
        """
        super().__init__(*args, **kwargs)

        # Assurer que le queryset du compte est trié
        self.fields['account'].queryset = Account.objects.all().order_by('name')

        # Logique pour pré-remplir les champs en mode édition (si une instance est fournie)
        if self.instance.pk:
            if self.instance.category:
                if self.instance.category.parent:
                    self.fields['category'].initial = self.instance.category.parent
                    self.fields['subcategory'].initial = self.instance.category
                    # Peupler le queryset de la sous-catégorie avec les enfants du parent
                    self.fields['subcategory'].queryset = self.instance.category.parent.children.all().order_by('name')
                else:
                    self.fields['category'].initial = self.instance.category
                    self.fields['subcategory'].queryset = Category.objects.none() # Aucune sous-catégorie pour une catégorie parent
            else:
                self.fields['category'].initial = None
                self.fields['subcategory'].initial = None
                self.fields['subcategory'].queryset = Category.objects.none()
            
            # Pré-remplir les tags pour l'édition
            if self.instance.tags.exists():
                self.fields['tags'].initial = self.instance.tags.all()
        
        # Ce bloc gère la re-soumission du formulaire (POST avec erreurs)
        # Il est crucial pour que la validation des sous-catégories fonctionne correctement
        # en s'assurant que l'option soumise est présente dans le queryset.
        if self.is_bound:
            main_category_id_from_post = self.data.get('category')
            submitted_subcategory_id = self.data.get('subcategory')

            # Initialiser le queryset de la sous-catégorie
            subcategory_queryset = Category.objects.none()

            # Si une catégorie principale a été soumise, peupler avec ses enfants
            if main_category_id_from_post:
                try:
                    main_category_from_post = Category.objects.get(pk=main_category_id_from_post)
                    subcategory_queryset = main_category_from_post.children.all()
                except Category.DoesNotExist:
                    pass # Le queryset reste vide si la catégorie principale n'existe pas

            # Si une sous-catégorie a été soumise, s'assurer qu'elle est dans le queryset
            if submitted_subcategory_id:
                try:
                    submitted_subcategory = Category.objects.get(pk=submitted_subcategory_id)
                    # Utiliser Q objects pour combiner les querysets si la sous-catégorie soumise
                    # n'est pas déjà dans le queryset généré par la catégorie principale.
                    # Vérifier que la sous-catégorie soumise est bien un enfant de la catégorie principale soumise (si présente)
                    if not main_category_id_from_post or (submitted_subcategory.parent and submitted_subcategory.parent.id == int(main_category_id_from_post)):
                        if submitted_subcategory not in subcategory_queryset:
                            subcategory_queryset = (subcategory_queryset | Category.objects.filter(pk=submitted_subcategory_id)).distinct()
                except Category.DoesNotExist:
                    pass # La sous-catégorie soumise n'existe pas, donc elle ne sera pas ajoutée.

            self.fields['subcategory'].queryset = subcategory_queryset.order_by('name')

        # Applique des classes Tailwind CSS à tous les champs du formulaire
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                # Appliquer les classes par défaut, sauf pour les CheckboxSelectMultiple
                if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                    field.widget.attrs.update({'class': 'p-2 border rounded-md w-full'})
                else:
                    # Pour les CheckboxSelectMultiple, appliquer des styles aux labels et inputs individuels
                    # (souvent géré par CSS direct ou par un custom widget si nécessaire)
                    pass # Les styles pour les cases à cocher seront gérés dans le template ou CSS


    def clean(self):
        """
        Valide les données du formulaire et assigne la catégorie finale à la transaction.
        Gère la logique entre catégorie principale et sous-catégorie.
        """
        cleaned_data = super().clean()
        main_category = cleaned_data.get('category')
        sub_category = cleaned_data.get('subcategory')
        # Les tags sont déjà gérés par ModelMultipleChoiceField, pas besoin de les traiter ici pour la validation de base.

        final_category = None

        # Règle 1: Au moins une catégorie (principale ou sous-catégorie) doit être sélectionnée.
        if not main_category and not sub_category:
            raise forms.ValidationError("Veuillez sélectionner une catégorie ou une sous-catégorie.")

        # Règle 2: Déterminer la catégorie finale pour le modèle Transaction.
        if sub_category:
            # Si une sous-catégorie est sélectionnée, elle doit avoir une catégorie parente
            # et cette catégorie parente doit correspondre à la catégorie principale sélectionnée (si elle l'est).
            if sub_category.parent and sub_category.parent == main_category:
                final_category = sub_category
            else:
                # La sous-catégorie sélectionnée n'a pas de parent ou ne correspond pas au parent sélectionné.
                # Cela peut arriver si l'utilisateur a manipulé le JS ou si une ancienne valeur est restée.
                self.add_error('subcategory', "La sous-catégorie sélectionnée n'est pas valide pour la catégorie principale choisie.")
        elif main_category:
            # Si seule une catégorie principale est sélectionnée, elle est utilisée.
            # Assurez-vous qu'elle n'a pas de parent. (Le queryset initial le garantit, mais une double-vérification est bonne).
            if main_category.parent is None:
                final_category = main_category
            else:
                # Ce cas ne devrait pas arriver si le queryset 'category' est bien filtré (parent__isnull=True)
                self.add_error('category', "La catégorie principale sélectionnée ne peut pas être une sous-catégorie.")
        
        # Assigner la catégorie finale déterminée au champ 'category' de l'instance du modèle.
        # Cela sera utilisé par form.save() pour définir la catégorie de la transaction.
        # Nous ajoutons 'final_category' aux cleaned_data pour que la vue puisse l'utiliser.
        cleaned_data['final_category'] = final_category

        # Si des erreurs ont été ajoutées, le formulaire n'est pas valide
        if self.errors:
            del cleaned_data['final_category'] # Supprimer pour éviter KeyError si la validation échoue plus tard

        return cleaned_data

