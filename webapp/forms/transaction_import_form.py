from django import forms
from webapp.models import Account

class TransactionImportForm(forms.Form):
    IMPORTER_CHOICES = [
        ('boursorama', 'Boursorama'),
        ('fortuneo', 'Fortuneo'),
        ('linxea', 'Linxea'),
        ('xml_iso', 'XML ISO 20022'),
        ('raiffeisen_csv', 'CSV Raiffeisen'),
        ('generic_csv', 'CSV Générique'),
        ('swift_mt940', 'SWIFT MT940'),
    ]
    
    account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        empty_label="Sélectionnez un compte",
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500'
        }),
        label="Compte de destination"
    )
    
    importer_type = forms.ChoiceField(
        choices=IMPORTER_CHOICES,
        widget=forms.Select(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500'
        }),
        label="Format d'importation"
    )
    
    csv_file = forms.FileField(
        widget=forms.FileInput(attrs={
            'class': 'w-full p-3 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500',
            'accept': '.csv,.xml,.txt,.mt940,.sta'
        }),
        label="Fichier à importer"
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['account'].queryset = Account.objects.filter(user=user)
