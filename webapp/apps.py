# webapp/apps.py
from django.apps import AppConfig

class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp'
    verbose_name = "Application de Budget Personnel" # Nom plus convivial pour l'admin

    def ready(self):
        """
        Méthode appelée lorsque l'application est prête.
        C'est l'endroit idéal pour importer les signaux afin qu'ils soient enregistrés.
        """
        import webapp.signals # Importez vos signaux ici pour qu'ils soient connectés

