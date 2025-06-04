# webapp/apps.py
# Ce fichier configure l'application Django 'webapp'.

from django.apps import AppConfig


class WebappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'webapp' # Le nom de votre application Django

    def ready(self):
        """
        Cette méthode est appelée lorsque Django démarre et que le registre des applications est prêt.
        Elle est utilisée ici pour importer admin.py, ce qui permet d'éviter les problèmes
        d'importation circulaire qui peuvent survenir lorsque les modèles sont enregistrés.
        """
        try:
            import webapp.admin  # Importe le module admin de cette application
        except ImportError:
            pass # Gère le cas où admin.py n'existe pas ou ne peut pas être importé

