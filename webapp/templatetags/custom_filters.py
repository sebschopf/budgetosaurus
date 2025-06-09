# webapp/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter(name='add_css')
def add_css(field, css):
    """
    Ajoute des classes CSS à un champ de formulaire.
    Utilisation: {{ field|add_css:"classe1 classe2" }}
    """
    return field.as_widget(attrs={"class": css})