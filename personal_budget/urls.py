# personal_budget/urls.py (Votre fichier urls.py principal du projet)

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.shortcuts import redirect # NOUVEAU: Importez redirect pour la vue de redirection

# NOUVEAU: Définition d'une vue simple qui redirige vers le tableau de bord
def profile_redirect_view(request):
    """
    Vue temporaire pour capturer la redirection par défaut de Django vers /accounts/profile/
    et rediriger immédiatement vers le tableau de bord.
    """
    return redirect(reverse_lazy('dashboard_view'))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('webapp.urls')), # 'webapp' est le nom de l'app

    # URLs d'authentification de Django (minimaliste et explicite)

    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html',
                                                redirect_authenticated_user=True,
                                                success_url=reverse_lazy('dashboard_view')),
         name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page=reverse_lazy('login')), name='logout'),

    # NOUVEAU: Capture la redirection par défaut de Django vers /accounts/profile/
    # et la redirige vers le tableau de bord.
    path('accounts/profile/', profile_redirect_view, name='profile_redirect'),

    # Optionnel: Si vous avez besoin d'autres URLs d'authentification (comme la réinitialisation de mot de passe)
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]
