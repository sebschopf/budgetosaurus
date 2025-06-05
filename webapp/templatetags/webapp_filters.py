# webapp/templatetags/webapp_filters.py
from django import template

register = template.Library()

@register.filter(name='get_field_label')
def get_field_label(form, field_name):
    """
    Retourne le label d'un champ de formulaire donné par son nom.
    Utilisé pour afficher les labels des champs dans les messages d'erreur de formset.
    """
    if field_name in form.fields:
        return form.fields[field_name].label
    return field_name # Retourne le nom du champ si le label n'est pas trouvé