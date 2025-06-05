# webapp/forms/transaction_import_form.py
from django import forms
from ..models import Account # Importation du modèle Account

class TransactionImportForm(forms.Form):
    """
    Formulaire pour télécharger un fichier de transactions,
    avec choix du type d'importateur et mappage des colonnes.
    """
    IMPORTER_CHOICES = [
        ('generic_csv', 'CSV Générique (Mappage des colonnes)'),
        ('raiffeisen_csv', 'CSV Raiffeisen (Format fixe: Date comptable, Libellé, Débit, Crédit)'),
        ('xml_iso', 'XML ISO 20022 (Non implémenté)'),
        ('swift_mt940', 'SWIFT MT940 (Non implémenté)'),
    ]

    csv_file = forms.FileField(
        label="Fichier de transactions",
        help_text="Téléchargez votre fichier de transactions.",
        widget=forms.ClearableFileInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    account = forms.ModelChoiceField(
        queryset=Account.objects.all().order_by('name'),
        empty_label="Sélectionner le compte de destination",
        label="Compte de destination",
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    
    importer_type = forms.ChoiceField(
        label="Type de fichier / Importateur",
        choices=IMPORTER_CHOICES,
        initial='generic_csv',
        widget=forms.Select(attrs={'class': 'p-2 border rounded-md w-full', 'id': 'id_importer_type'})
    )

    # Champs pour le mappage des colonnes
    date_column = forms.CharField(
        label="Nom de la colonne Date",
        help_text="Nom exact de la colonne contenant la date (ex: 'Date', 'Date de l\'opération').",
        required=False,
        widget=forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    description_column = forms.CharField(
        label="Nom de la colonne Description",
        help_text="Nom exact de la colonne contenant la description (ex: 'Description', 'Libellé').",
        required=False,
        widget=forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )
    amount_column = forms.CharField(
        label="Nom de la colonne Montant",
        help_text="Nom exact de la colonne contenant le montant (ex: 'Montant', 'Débit', 'Crédit').",
        required=False,
        widget=forms.TextInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            importer_type = self.data.get('importer_type')
        else:
            importer_type = self.initial.get('importer_type', 'generic_csv')

        if importer_type == 'generic_csv':
            self.fields['date_column'].initial = self.fields['date_column'].initial or 'Date'
            self.fields['description_column'].initial = self.fields['description_column'].initial or 'Description'
            self.fields['amount_column'].initial = self.fields['amount_column'].initial or 'Montant'
        elif importer_type == 'raiffeisen_csv':
            self.fields['date_column'].initial = 'Date comptable'
            self.fields['description_column'].initial = 'Libellé'
            self.fields['amount_column'].initial = 'Débit/Crédit (format fixe)'
            self.fields['date_column'].widget.attrs['readonly'] = True
            self.fields['description_column'].widget.attrs['readonly'] = True
            self.fields['amount_column'].widget.attrs['readonly'] = True
            self.fields['date_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['description_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['amount_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
        elif importer_type == 'xml_iso':
            self.fields['date_column'].initial = 'Non applicable'
            self.fields['description_column'].initial = 'Non applicable'
            self.fields['amount_column'].initial = 'Non applicable'
            self.fields['date_column'].widget.attrs['readonly'] = True
            self.fields['description_column'].widget.attrs['readonly'] = True
            self.fields['amount_column'].widget.attrs['readonly'] = True
            self.fields['date_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['description_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['amount_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
        elif importer_type == 'swift_mt940':
            self.fields['date_column'].initial = 'Non applicable'
            self.fields['description_column'].initial = 'Non applicable'
            self.fields['amount_column'].initial = 'Non applicable'
            self.fields['date_column'].widget.attrs['readonly'] = True
            self.fields['description_column'].widget.attrs['readonly'] = True
            self.fields['amount_column'].widget.attrs['readonly'] = True
            self.fields['date_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['description_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."
            self.fields['amount_column'].help_text = "Le mappage n'est pas nécessaire pour ce format."


    def clean(self):
        cleaned_data = super().clean()
        importer_type = cleaned_data.get('importer_type')

        if importer_type == 'generic_csv':
            if not cleaned_data.get('date_column'):
                self.add_error('date_column', "Ce champ est requis pour l'importateur CSV générique.")
            if not cleaned_data.get('description_column'):
                self.add_error('description_column', "Ce champ est requis pour l'importateur CSV générique.")
            if not cleaned_data.get('amount_column'):
                self.add_error('amount_column', "Ce champ est requis pour l'importateur CSV générique.")
        
        return cleaned_data
