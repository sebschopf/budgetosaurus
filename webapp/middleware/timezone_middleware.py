# webapp/middleware/timezone_middleware.py

from django.utils import timezone
import pytz
from django.conf import settings

class TimezoneMiddleware:
    """
    Middleware pour activer le fuseau horaire de l'utilisateur pour chaque requête.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Tente d'accéder au profil utilisateur pour récupérer le fuseau horaire
                # Notez l'utilisation de 'request.user.profile' car nous avons défini related_name='profile'
                user_timezone = request.user.profile.timezone
                timezone.activate(pytz.timezone(user_timezone))
            except (AttributeError, pytz.UnknownTimeZoneError):
                # Si le profil n'existe pas, ou le fuseau horaire est invalide,
                # on désactive le fuseau horaire, ce qui fait revenir à la configuration par défaut de Django
                timezone.deactivate()
        else:
            # Pour les utilisateurs non authentifiés, on désactive le fuseau horaire
            # afin que les dates soient affichées dans le fuseau horaire par défaut du serveur (souvent UTC)
            timezone.deactivate()

        response = self.get_response(request)
        # Il est bonne pratique de désactiver le fuseau horaire après la requête
        # pour éviter des fuites de configuration entre les requêtes.
        timezone.deactivate()
        return response