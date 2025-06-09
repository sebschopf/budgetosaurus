# webapp/forms/transaction_form.py
from django import forms
from ..models import Transaction, Category, Account, Tag
from django.db.models import Q

class TransactionForm(forms.ModelForm):
    """
    Formulaire pour ajouter et modifier des transactions, avec des listes déroulantes
    dynamiques pour les catégories et sous-catégories, et un champ pour les tags.
    Maintenant, il filtre les choix par l'utilisateur connecté.
    """
    # Champ pour la catégorie parente (niveau supérieur)
    # Le queryset est filtré dynamiquement dans __init__ en fonction de l'utilisateur.
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ, sera peuplé dynamiquement
        empty_label="Sélectionner une catégorie parente",
        required=False,
        label="Catégorie Principale"
    )

    # Champ pour la sous-catégorie
    # Ce champ est initialement vide et sera rempli dynamiquement par JavaScript.
    subcategory = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ
        empty_label="Sélectionner une sous-catégorie",
        required=False,
        label="Sous-catégorie"
    )

    # Nouveau champ pour les tags
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(), # Queryset vide au départ, sera peuplé dynamiquement
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags"
    )

    class Meta:
        model = Transaction
        fields = ['date', 'description', 'amount', 'category', 'subcategory', 'account', 'transaction_type', 'tags']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'p-2 border rounded-md w-full'}),
            'amount': forms.NumberInput(attrs={'step': '0.01', 'class': 'p-2 border rounded-md w-full'}),
            'description': forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full', 'list': 'commonDescriptionsList'}),
            'account': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
            'transaction_type': forms.Select(attrs={'class': 'p-2 border rounded-md w-full'}),
        }

    # Ajouter 'user' au constructeur du formulaire
    def __init__(self, *args, **kwargs):
        # Récupérer l'utilisateur passé comme argument avant d'appeler super().__init__
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            # Filtrer les comptes par l'utilisateur connecté
            self.fields['account'].queryset = Account.objects.filter(user=self.user).order_by('name')
            # Filtrer les catégories parentes par l'utilisateur connecté
            self.fields['category'].queryset = Category.objects.filter(user=self.user, parent__isnull=True).order_by('name')
            # Filtrer les tags par l'utilisateur connecté
            self.fields['tags'].queryset = Tag.objects.filter(user=self.user).order_by('name')
        else:
            # Si aucun utilisateur n'est passé (ce qui ne devrait pas arriver avec @login_required),
            # s'assurer que les querysets sont vides pour éviter l'affichage de données non filtrées.
            self.fields['account'].queryset = Account.objects.none()
            self.fields['category'].queryset = Category.objects.none()
            self.fields['tags'].queryset = Tag.objects.none()


        # Logique pour pré-remplir les champs en mode édition (si une instance est fournie)
        if self.instance.pk:
            if self.instance.category:
                if self.instance.category.parent:
                    self.fields['category'].initial = self.instance.category.parent
                    self.fields['subcategory'].initial = self.instance.category
                    # Filtrer les sous-catégories par l'utilisateur connecté
                    self.fields['subcategory'].queryset = self.instance.category.parent.children.filter(user=self.user).order_by('name')
                else:
                    self.fields['category'].initial = self.instance.category
                    self.fields['subcategory'].queryset = Category.objects.none()
            else:
                self.fields['category'].initial = None
                self.fields['subcategory'].initial = None
                self.fields['subcategory'].queryset = Category.objects.none()

            # Pré-remplir les tags pour l'édition (déjà géré par ModelForm mais bien de vérifier)
            if self.instance.tags.exists():
                self.fields['tags'].initial = self.instance.tags.all()

        # Ce bloc gère la re-soumission du formulaire (POST avec erreurs)
        if self.is_bound:
            main_category_id_from_post = self.data.get('category')
            submitted_subcategory_id = self.data.get('subcategory')

            subcategory_queryset = Category.objects.none()

            if main_category_id_from_post:
                try:
                    # Récupérer la catégorie principale soumise POUR L'UTILISATEUR CONNECTÉ
                    main_category_from_post = Category.objects.get(pk=main_category_id_from_post, user=self.user)
                    # Filtrer les enfants par l'utilisateur connecté
                    subcategory_queryset = main_category_from_post.children.filter(user=self.user)
                except Category.DoesNotExist:
                    pass

            if submitted_subcategory_id:
                try:
                    # Récupérer la sous-catégorie soumise POUR L'UTILISATEUR CONNECTÉ
                    submitted_subcategory = Category.objects.get(pk=submitted_subcategory_id, user=self.user)
                    if not main_category_id_from_post or (submitted_subcategory.parent and submitted_subcategory.parent.id == int(main_category_id_from_post)):
                        if submitted_subcategory not in subcategory_queryset:
                            subcategory_queryset = (subcategory_queryset | Category.objects.filter(pk=submitted_subcategory_id, user=self.user)).distinct()
                except Category.DoesNotExist:
                    pass

            self.fields['subcategory'].queryset = subcategory_queryset.order_by('name')

        # Applique des classes Tailwind CSS à tous les champs du formulaire
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                    field.widget.attrs.update({'class': 'p-2 border rounded-md w-full'})
                else:
                    pass # Les styles pour les cases à cocher seront gérés dans le template ou CSS


    def clean(self):
        """
        Valide les données du formulaire et assigne la catégorie finale à la transaction.
        Gère la logique entre catégorie principale et sous-catégorie.
        """
        cleaned_data = super().clean()
        main_category = cleaned_data.get('category')
        sub_category = cleaned_data.get('subcategory')

        final_category = None

        if not main_category and not sub_category:
            raise forms.ValidationError("Veuillez sélectionner une catégorie ou une sous-catégorie.")

        if sub_category:
            if sub_category.parent and sub_category.parent == main_category:
                final_category = sub_category
            else:
                self.add_error('subcategory', "La sous-catégorie sélectionnée n'est pas valide pour la catégorie principale choisie.")
        elif main_category:
            if main_category.parent is None:
                final_category = main_category
            else:
                self.add_error('category', "La catégorie principale sélectionnée ne peut pas être une sous-catégorie.")

        cleaned_data['final_category'] = final_category

        if self.errors:
            del cleaned_data['final_category']

        return cleaned_data
