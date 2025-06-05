# webapp/forms/category_import_form.py
from django import forms

class CategoryImportForm(forms.Form):
    """
    Formulaire pour télécharger un fichier CSV afin d'importer des catégories.
    """
    csv_file = forms.FileField(
        label="Fichier CSV de catégories",
        help_text="Téléchargez un fichier CSV avec les colonnes 'name' et 'parent_name' (optionnel).",
        widget=forms.ClearableFileInput(attrs={'class': 'p-2 border rounded-md w-full'})
    )
