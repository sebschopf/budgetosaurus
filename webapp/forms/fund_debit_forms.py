# webapp/forms/fund_debit_forms.py
from django import forms
from django.forms import formset_factory
from ..models import Category, Transaction, FundDebitRecord, FundDebitLine

class FundDebitRecordForm(forms.ModelForm):
    """
    Formulaire principal pour la création ou la modification d'un enregistrement de débit de fonds.
    Il est lié à une Transaction de dépense.
    """
    class Meta:
        model = FundDebitRecord
        fields = ['notes'] # La transaction est passée via la vue
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes sur ce débit de fonds', 'class': 'p-2 border rounded-md w-full'})
        }

class FundDebitLineForm(forms.ModelForm):
    """
    Formulaire pour une seule ligne de débit de fonds, débitant un montant d'une catégorie spécifique.
    Maintenant, il filtre les choix de catégorie par l'utilisateur connecté.
    """
    # Champ pour la catégorie qui gère un fonds (vos enveloppes)
    category = forms.ModelChoiceField(
        queryset=Category.objects.none(), # Queryset vide au départ, sera filtré dans __init__
        empty_label="Sélectionner le Fonds (Catégorie)",
        required=True,
        label="Fonds / Enveloppe",
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full split-category-main'}) # Réutilisation de la classe pour cohérence JS
    )
    amount = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Montant à débiter', 'class': 'p-2 border rounded-md w-full'})
    )

    class Meta:
        model = FundDebitLine
        fields = ['category', 'amount', 'notes']
        widgets = {
            'notes': forms.TextInput(attrs={'placeholder': 'Note pour cette ligne (optionnel)', 'class': 'p-2 border rounded-md w-full'})
        }

    # Accepte l'utilisateur dans le constructeur
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None) # Récupère l'utilisateur
        super().__init__(*args, **kwargs)

        if self.user:
            # Filtrer les catégories gérées par fonds par l'utilisateur connecté
            self.fields['category'].queryset = Category.objects.filter(user=self.user, is_fund_managed=True).order_by('name')
        else:
            # Si aucun utilisateur n'est passé, le queryset est vide (sécurité)
            self.fields['category'].queryset = Category.objects.none()

        # Si le formulaire est lié (POST) ou a des données initiales (GET pour édition),
        # assurez-vous que la catégorie sélectionnée, si elle existe, est toujours dans le queryset.
        if self.is_bound or self.initial:
            selected_category_id = None
            if self.is_bound:
                selected_category_id = self.data.get(f'{self.prefix}-category')
            elif self.instance.pk: # Pour l'édition d'une ligne existante
                selected_category_id = self.instance.category.id

            if selected_category_id:
                try:
                    # S'assurer que la catégorie sélectionnée appartient à l'utilisateur
                    selected_category = Category.objects.get(pk=selected_category_id, user=self.user)
                    # Si la catégorie est déjà dans le queryset, inutile de l'ajouter à nouveau
                    if selected_category not in self.fields['category'].queryset:
                        # Utilisez Q pour combiner les querysets si la catégorie n'est pas déjà présente
                        self.fields['category'].queryset = (
                            self.fields['category'].queryset |
                            Category.objects.filter(pk=selected_category_id, user=self.user)
                        ).distinct()
                except Category.DoesNotExist:
                    # La catégorie sélectionnée n'existe pas ou n'appartient pas à l'utilisateur
                    pass


    # Ajout de la validation personnalisée pour s'assurer que la catégorie appartient à l'utilisateur
    def clean_category(self):
        category = self.cleaned_data.get('category')
        if category and category.user != self.user:
            raise forms.ValidationError("Cette catégorie n'appartient pas à votre compte.")
        return category


# Crée un formset pour gérer plusieurs lignes de débit de fonds au sein d'un seul enregistrement
# Le formset_factory est appelé sans l'argument 'user' ici. L'utilisateur sera passé
# à chaque formulaire individuel via le paramètre 'form_kwargs' lors de l'instanciation
# du formset dans la vue.
FundDebitLineFormset = formset_factory(FundDebitLineForm, extra=1, can_delete=True)
