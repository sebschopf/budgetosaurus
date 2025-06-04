from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Importer admin ici pour s'assurer qu'il est chargé après la création de l'application
        try:
            import core.admin
        except ImportError:
            pass