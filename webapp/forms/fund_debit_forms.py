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
    """
    # Champ pour la catégorie qui gère un fonds (vos enveloppes)
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_fund_managed=True).order_by('name'),
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

# Crée un formset pour gérer plusieurs lignes de débit de fonds au sein d'un seul enregistrement
FundDebitLineFormset = formset_factory(FundDebitLineForm, extra=1, can_delete=True)

