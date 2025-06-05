# webapp/forms/allocation_forms.py
from django import forms
from django.forms import formset_factory
from ..models import Category, Transaction, Allocation, AllocationLine

class AllocationForm(forms.ModelForm):
    """
    Formulaire principal pour la création ou la modification d'une Allocation.
    Il est lié à une Transaction de revenu.
    """
    class Meta:
        model = Allocation
        fields = ['notes'] # La transaction est passée via la vue
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Notes sur cette allocation', 'class': 'p-2 border rounded-md w-full'})
        }

class AllocationLineForm(forms.ModelForm):
    """
    Formulaire pour une seule ligne d'allocation, allouant un montant à une catégorie spécifique.
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
        widget=forms.NumberInput(attrs={'step': '0.01', 'placeholder': 'Montant alloué', 'class': 'p-2 border rounded-md w-full'})
    )

    class Meta:
        model = AllocationLine
        fields = ['category', 'amount', 'notes']
        widgets = {
            'notes': forms.TextInput(attrs={'placeholder': 'Note pour cette ligne (optionnel)', 'class': 'p-2 border rounded-md w-full'})
        }

# Crée un formset pour gérer plusieurs lignes d'allocation au sein d'une seule allocation
AllocationLineFormset = formset_factory(AllocationLineForm, extra=1, can_delete=True)

