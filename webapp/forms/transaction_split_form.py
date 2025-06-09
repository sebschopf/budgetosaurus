# webapp/forms/transaction_split_form.py
from django import forms
from django.forms import formset_factory
from ..models import Category, Transaction

class SplitTransactionLineForm(forms.Form):
    """
    Formulaire pour une seule ligne de division d'une transaction.
    Maintenant, il filtre les choix de catégorie par l'utilisateur connecté.
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
    # Le queryset sera filtré dynamiquement dans __init__ en fonction de l'utilisateur.
    main_category = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ
        empty_label="Sélectionner Catégorie Principale",
        required=True,
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full split-category-main'})
    )
    # Champ pour la sous-catégorie (initialement vide, rempli par JS)
    # Le queryset sera filtré dynamiquement dans __init__ et par JS.
    subcategory = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ
        empty_label="Sélectionner Sous-catégorie",
        required=False,
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full split-category subcategory-hidden'})
    )

    # Accepte l'utilisateur dans le constructeur
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Récupère l'utilisateur
        super().__init__(*args, **kwargs)

        if self.user:
            # Filtrer les catégories principales par l'utilisateur connecté
            self.fields['main_category'].queryset = Category.objects.filter(user=self.user, parent__isnull=True).order_by('name')
        else:
            # Si aucun utilisateur n'est passé, les querysets sont vides (sécurité)
            self.fields['main_category'].queryset = Category.objects.none()
            self.fields['subcategory'].queryset = Category.objects.none() # Assurer que la sous-catégorie est aussi vide

        # Si le formulaire est lié (POST) ou a des données initiales (GET pour édition)
        if self.is_bound or self.initial:
            main_category_id = None
            if self.is_bound:
                # self.prefix est important pour récupérer les données du formset
                main_category_id = self.data.get(f'{self.prefix}-main_category')
            elif self.initial:
                main_category_id = self.initial.get('main_category')

            if main_category_id:
                try:
                    # Récupérer la catégorie principale POUR L'UTILISATEUR CONNECTÉ
                    main_category_instance = Category.objects.get(pk=main_category_id, user=self.user)
                    # Filtrer les enfants par l'utilisateur connecté
                    self.fields['subcategory'].queryset = main_category_instance.children.filter(user=self.user).order_by('name')
                except Category.DoesNotExist:
                    self.fields['subcategory'].queryset = Category.objects.none()


    def clean(self):
        """
        Validation personnalisée pour s'assurer qu'une catégorie finale est sélectionnée
        et que la sous-catégorie, si présente, appartient bien à la catégorie principale.
        """
        cleaned_data = super().clean()

        # Récupérer les objets Category filtrés par l'utilisateur si disponibles
        main_category = cleaned_data.get('main_category')
        subcategory = cleaned_data.get('subcategory')

        final_category_object = None

        if main_category:
            # Vérifier que la catégorie principale appartient bien à l'utilisateur connecté
            if main_category.user != self.user:
                self.add_error('main_category', "Cette catégorie n'appartient pas à votre compte.")

            if subcategory:
                # Vérifier que la sous-catégorie appartient bien à l'utilisateur connecté
                if subcategory.user != self.user:
                    self.add_error('subcategory', "Cette sous-catégorie n'appartient pas à votre compte.")
                # S'assurer que la sous-catégorie appartient à la catégorie principale
                elif subcategory.parent != main_category:
                    self.add_error('subcategory', "Cette sous-catégorie n'appartient pas à la catégorie principale sélectionnée.")
                final_category_object = subcategory
            else:
                final_category_object = main_category
        else:
            if not self.errors.get('main_category'):
                self.add_error('main_category', "Veuillez sélectionner une catégorie principale.")

        cleaned_data['final_category'] = final_category_object

        if self.errors:
            del cleaned_data['final_category']

        return cleaned_data

# Création du formset pour gérer plusieurs instances de SplitTransactionLineForm
# Le formset_factory est appelé sans l'argument 'user' ici. L'utilisateur sera passé
# à chaque formulaire individuel via le paramètre 'form_kwargs' lors de l'instanciation
# du formset dans la vue.
SplitTransactionFormset = formset_factory(SplitTransactionLineForm, extra=1, can_delete=True)
