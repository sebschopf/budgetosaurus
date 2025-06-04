# personal_budget/urls.py (Votre fichier urls.py principal du projet)

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('webapp.urls')), # Assurez-vous que 'webapp' est le nom de votre app
    # Si votre page d'accueil est directement /budget/, utilisez path('', include('webapp.urls'))
    # ou redirigez depuis la racine si nécessaire.
]