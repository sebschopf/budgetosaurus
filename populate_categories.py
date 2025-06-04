# populate_categories.py
import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_budget.settings')
django.setup()

from core.models import Category
from django.core.exceptions import ValidationError

print("Populating categories...")

# Clear existing categories (optional, useful for re-running the script)
# Category.objects.all().delete()
# print("Existing categories cleared.")

# 1. Créer les catégories de premier niveau (parents)
depenses_fixes, _ = Category.objects.get_or_create(name="Dépenses Fixes")
depenses_courantes, _ = Category.objects.get_or_create(name="Dépenses Courantes")
depenses_occasionnelles, _ = Category.objects.get_or_create(name="Dépenses Occasionnelles")
revenus, _ = Category.objects.get_or_create(name="Revenus")
objectifs_epargne, _ = Category.objects.get_or_create(name="Objectifs d'Épargne")

print("First level categories created/retrieved.")

# 2. Créer les catégories intermédiaires (parents des feuilles)
logement, _ = Category.objects.get_or_create(name="Logement", parent=depenses_fixes)
assurances, _ = Category.objects.get_or_create(name="Assurances", parent=depenses_fixes)
services, _ = Category.objects.get_or_create(name="Services", parent=depenses_fixes)
transport_fixe, _ = Category.objects.get_or_create(name="Transport (Fixe)", parent=depenses_fixes)
emprunts_dettes, _ = Category.objects.get_or_create(name="Emprunts et Dettes", parent=depenses_fixes)
sante, _ = Category.objects.get_or_create(name="Santé", parent=depenses_fixes)

alimentation, _ = Category.objects.get_or_create(name="Alimentation", parent=depenses_courantes)
habillement, _ = Category.objects.get_or_create(name="Habillement", parent=depenses_courantes)
entretien_maison, _ = Category.objects.get_or_create(name="Entretien de la Maison", parent=depenses_courantes)
transport_courant, _ = Category.objects.get_or_create(name="Transport (Courant)", parent=depenses_courantes)
loisirs_courants, _ = Category.objects.get_or_create(name="Loisirs (Courants)", parent=depenses_courantes)

evenements, _ = Category.objects.get_or_create(name="Événements", parent=depenses_occasionnelles)
voyages, _ = Category.objects.get_or_create(name="Voyages", parent=depenses_occasionnelles)
achats_ponctuels, _ = Category.objects.get_or_create(name="Achats Ponctuels", parent=depenses_occasionnelles)
reparations_imprevues, _ = Category.objects.get_or_create(name="Réparations Imprévues", parent=depenses_occasionnelles)

print("Intermediate categories created/retrieved.")

# 3. Créer les catégories de feuilles (où les transactions seront affectées)
# Utilisation de get_or_create pour éviter les doublons si le script est exécuté plusieurs fois
Category.objects.get_or_create(name="Loyer", parent=logement)
Category.objects.get_or_create(name="Hypothèque", parent=logement)
Category.objects.get_or_create(name="Frais de copropriété", parent=logement)
Category.objects.get_or_create(name="Taxes immobilières", parent=logement)
Category.objects.get_or_create(name="Assurance Habitation", parent=assurances)
Category.objects.get_or_create(name="Assurance Responsabilité Civile", parent=assurances)
Category.objects.get_or_create(name="Électricité", parent=services)
Category.objects.get_or_create(name="Gaz", parent=services)
Category.objects.get_or_create(name="Eau", parent=services)
Category.objects.get_or_create(name="Internet", parent=services)
Category.objects.get_or_create(name="Téléphone", parent=services)
Category.objects.get_or_create(name="Carburant (Fixe)", parent=transport_fixe) # Renommé pour clarté
Category.objects.get_or_create(name="Transports en commun", parent=transport_fixe)
Category.objects.get_or_create(name="Assurance Automobile", parent=transport_fixe)
Category.objects.get_or_create(name="Remboursements de crédits", parent=emprunts_dettes)
Category.objects.get_or_create(name="Assurances maladie", parent=sante)
Category.objects.get_or_create(name="Frais médicaux", parent=sante)

Category.objects.get_or_create(name="Courses Alimentaires", parent=alimentation)
Category.objects.get_or_create(name="Restaurants", parent=alimentation)
Category.objects.get_or_create(name="Vêtements", parent=habillement)
Category.objects.get_or_create(name="Chaussures", parent=habillement)
Category.objects.get_or_create(name="Produits d'entretien", parent=entretien_maison)
Category.objects.get_or_create(name="Réparations Maison", parent=entretien_maison)
Category.objects.get_or_create(name="Carburant (Courant)", parent=transport_courant)
Category.objects.get_or_create(name="Réparations Auto (Courant)", parent=transport_courant)
Category.objects.get_or_create(name="Sorties", parent=loisirs_courants)
Category.objects.get_or_create(name="Vacances (Courantes)", parent=loisirs_courants)

Category.objects.get_or_create(name="Mariages/Enterrements", parent=evenements)
Category.objects.get_or_create(name="Voyages (Occasionnels)", parent=voyages)
Category.objects.get_or_create(name="Électroménager", parent=achats_ponctuels)
Category.objects.get_or_create(name="Meubles", parent=achats_ponctuels)
Category.objects.get_or_create(name="Remplacement Appareils", parent=reparations_imprevues)

# Pour les revenus
Category.objects.get_or_create(name="Salaire", parent=revenus)
Category.objects.get_or_create(name="Bonus", parent=revenus)
Category.objects.get_or_create(name="Intérêts", parent=revenus)
Category.objects.get_or_create(name="Remboursements", parent=revenus)

# Pour les objectifs d'épargne
Category.objects.get_or_create(name="Vacances (Épargne)", parent=objectifs_epargne)
Category.objects.get_or_create(name="Impôts Annuels", parent=objectifs_epargne)
Category.objects.get_or_create(name="Achat Voiture", parent=objectifs_epargne)

print(f"Total categories created: {Category.objects.count()}")
print("Category population complete.")