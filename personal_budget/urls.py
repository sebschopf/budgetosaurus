# personal_budget/urls.py (Votre fichier urls.py principal du projet)

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('webapp.urls')), # 'webapp' est le nom de l'app
    # Page d'accueil est directement /budget/, utiliser path('', include('webapp.urls'))
]