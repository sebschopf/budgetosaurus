# webapp/views/glossary.py
from django.shortcuts import render

def glossary_view(request):
    """
    Vue affichant la page du glossaire avec les définitions des concepts clés.
    """
    context = {
        'page_title': 'Glossaire des Concepts',
    }
    return render(request, 'webapp/glossary.html', context)
