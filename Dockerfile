# Dockerfile

# Utilise une image Python officielle comme base
FROM python:3.11-slim-bookworm

# Définit le répertoire de travail dans le conteneur
WORKDIR /app

# Copie le fichier requirements.txt dans le répertoire de travail
COPY requirements.txt /app/

# Installe les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie tout le reste du projet dans le répertoire de travail
COPY . /app/

# Rend le port 8000 disponible pour l'extérieur du conteneur (pour le serveur Django)
EXPOSE 8000

# Commande par défaut pour lancer le serveur Django
# Utilise Gunicorn pour un serveur de production plus robuste
# -b 0.0.0.0:8000 pour écouter sur toutes les interfaces, sur le port 8000
# personal_budget.wsgi:application fait référence au module WSGI de votre projet Django
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "personal_budget.wsgi:application"]