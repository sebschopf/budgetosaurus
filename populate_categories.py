# populate_categories.py
import os
import django

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'personal_budget.settings')
django.setup()

from webapp.models import Category, Tag # Importez le modèle Tag
from django.core.exceptions import ValidationError

print("Populating categories and tags...")

# Clear existing categories and tags (optional, useful for re-running the script)
# ATTENTION: Cela supprimera TOUTES les catégories et tags existants et leurs relations.
# Décommentez les lignes ci-dessous si vous voulez vider la base de données de catégories/tags avant de recréer.
Category.objects.all().delete()
Tag.objects.all().delete()
# print("Existing categories and tags cleared.")

# --- 1. Créer les catégories de premier niveau (parents) ---
# Ces catégories seront visibles dans le premier sélecteur du formulaire de transaction.
revenus, _ = Category.objects.get_or_create(name="Revenus", defaults={'description': "Sources d'argent entrant."})
logement, _ = Category.objects.get_or_create(name="Logement", defaults={'description': "Dépenses liées à l'habitation."})
transport, _ = Category.objects.get_or_create(name="Transport", defaults={'description': "Dépenses liées aux déplacements."})
sante_bien_etre, _ = Category.objects.get_or_create(name="Santé & Bien-être", defaults={'description': "Dépenses de santé, assurances et bien-être personnel."})
alimentation_restauration, _ = Category.objects.get_or_create(name="Alimentation & Restauration", defaults={'description': "Dépenses de nourriture et repas à l'extérieur."})
habillement_soins, _ = Category.objects.get_or_create(name="Habillement & Soins Personnels", defaults={'description': "Dépenses de vêtements, chaussures et produits d'hygiène/beauté."})
loisirs_culture, _ = Category.objects.get_or_create(name="Loisirs & Culture", defaults={'description': "Dépenses pour les divertissements, hobbies, culture et voyages."})
finances_impots, _ = Category.objects.get_or_create(name="Finances & Impôts", defaults={'description': "Dépenses liées aux impôts, crédits et frais financiers."})
animaux, _ = Category.objects.get_or_create(name="Animaux", defaults={'description': "Dépenses pour les animaux de compagnie."})
dons_cotisations, _ = Category.objects.get_or_create(name="Dons & Cotisations", defaults={'description': "Dons, charité et cotisations à des organisations."})
achats_divers_imprevus, _ = Category.objects.get_or_create(name="Achats Divers & Imprévus", defaults={'description': "Achats non récurrents et dépenses imprévues."})

print("First level categories created/retrieved.")

# --- 2. Créer les sous-catégories (enfants) ---
# Ces catégories seront visibles dans le deuxième sélecteur du formulaire de transaction,
# après la sélection de leur catégorie parente respective.

# Revenus
Category.objects.get_or_create(name="Salaire", parent=revenus)
Category.objects.get_or_create(name="Bonus", parent=revenus)
Category.objects.get_or_create(name="Intérêts", parent=revenus)
Category.objects.get_or_create(name="Remboursements Reçus", parent=revenus)
Category.objects.get_or_create(name="Autres Revenus", parent=revenus)

# Logement
Category.objects.get_or_create(name="Loyer / Hypothèque", parent=logement)
Category.objects.get_or_create(name="Charges Copropriété / Taxes Immobilières", parent=logement)
Category.objects.get_or_create(name="Électricité", parent=logement)
Category.objects.get_or_create(name="Gaz", parent=logement)
Category.objects.get_or_create(name="Eau", parent=logement)
Category.objects.get_or_create(name="Internet", parent=logement)
Category.objects.get_or_create(name="Téléphone / Abonnements Médias", parent=logement) # Regroupe Téléphone et abonnements TV/Streaming
Category.objects.get_or_create(name="Assurance Habitation / Ménage", parent=logement)
Category.objects.get_or_create(name="Réparations & Entretien Maison", parent=logement)
Category.objects.get_or_create(name="Jardinage", parent=logement) # Pour balcon

# Transport
Category.objects.get_or_create(name="Abonnements Transports", parent=transport) # TPG, CFF Demi-Tarif
Category.objects.get_or_create(name="Tickets Transports", parent=transport) # Train, bus occasionnel
Category.objects.get_or_create(name="Carburant", parent=transport)
Category.objects.get_or_create(name="Entretien & Réparations Véhicule", parent=transport) # Voiture, vélo
Category.objects.get_or_create(name="Parking / Péage", parent=transport) # Vignette autoroute
Category.objects.get_or_create(name="Assurance Automobile", parent=transport)

# Santé & Bien-être
Category.objects.get_or_create(name="Assurance Maladie (Cotisation)", parent=sante_bien_etre)
Category.objects.get_or_create(name="Frais Médicaux (Consultations)", parent=sante_bien_etre)
Category.objects.get_or_create(name="Médicaments", parent=sante_bien_etre)
Category.objects.get_or_create(name="Cote-part Assurance Maladie", parent=sante_bien_etre) # Ex: Swica
Category.objects.get_or_create(name="Soins Corporels & Bien-être", parent=sante_bien_etre) # Massage, coiffeur, esthétique
Category.objects.get_or_create(name="Activités Sportives", parent=sante_bien_etre) # Piscine, fitness, cours de sport

# Alimentation & Restauration
Category.objects.get_or_create(name="Courses Alimentaires", parent=alimentation_restauration)
Category.objects.get_or_create(name="Restaurants / Plats à Emporter", parent=alimentation_restauration)
Category.objects.get_or_create(name="Boulangerie / Cafés", parent=alimentation_restauration)

# Habillement & Soins Personnels
Category.objects.get_or_create(name="Vêtements", parent=habillement_soins)
Category.objects.get_or_create(name="Chaussures", parent=habillement_soins)
Category.objects.get_or_create(name="Vêtements de Sport", parent=habillement_soins)
Category.objects.get_or_create(name="Accessoires Habillement", parent=habillement_soins)
Category.objects.get_or_create(name="Produits de Beauté / Hygiène", parent=habillement_soins)

# Loisirs & Culture
Category.objects.get_or_create(name="Sorties & Divertissements", parent=loisirs_culture) # Cinéma, concerts, musées
Category.objects.get_or_create(name="Vacances & Voyages", parent=loisirs_culture) # Dépenses sur place, hors transport/hébergement si déjà catégorisés
Category.objects.get_or_create(name="Livres & Médias", parent=loisirs_culture)
Category.objects.get_or_create(name="Hobbies & Matériel", parent=loisirs_culture)
Category.objects.get_or_create(name="Cadeaux Offerts", parent=loisirs_culture)
Category.objects.get_or_create(name="Tabac / E-cigarettes", parent=loisirs_culture)

# Finances & Impôts
Category.objects.get_or_create(name="Impôts Annuels", parent=finances_impots)
Category.objects.get_or_create(name="Remboursements de Crédits / Emprunts", parent=finances_impots)
Category.objects.get_or_create(name="Frais Bancaires", parent=finances_impots)
Category.objects.get_or_create(name="Investissements (3ème Pilier, Or)", parent=finances_impots) # Pour Gold Avenue, 3ème pilier

# Animaux
Category.objects.get_or_create(name="Nourriture Animaux", parent=animaux)
Category.objects.get_or_create(name="Vétérinaire", parent=animaux)
Category.objects.get_or_create(name="Pension / Garde Animaux", parent=animaux)
Category.objects.get_or_create(name="Jouets & Accessoires Animaux", parent=animaux)

# Dons & Cotisations
Category.objects.get_or_create(name="Donations / Charité", parent=dons_cotisations)
Category.objects.get_or_create(name="Cotisations Associations / Clubs", parent=dons_cotisations)

# Achats Divers & Imprévus
Category.objects.get_or_create(name="Électroménager", parent=achats_divers_imprevus)
Category.objects.get_or_create(name="Meubles", parent=achats_divers_imprevus)
Category.objects.get_or_create(name="Remplacement Appareils", parent=achats_divers_imprevus)
Category.objects.get_or_create(name="Autres Achats Divers", parent=achats_divers_imprevus) # Pour ce qui est vraiment unique
Category.objects.get_or_create(name="Réparations Imprévues", parent=achats_divers_imprevus) # Hors maison/auto

print(f"Total categories created: {Category.objects.count()}")

# --- 3. Créer les Tags ---
# Ces tags peuvent être associés à n'importe quelle transaction pour une analyse transversale.
Tag.objects.get_or_create(name="Fixe", defaults={'description': "Dépense ou revenu dont le montant et la fréquence sont réguliers."})
Tag.objects.get_or_create(name="Variable", defaults={'description': "Dépense ou revenu dont le montant ou la fréquence peuvent varier."})
Tag.objects.get_or_create(name="Essentiel", defaults={'description': "Dépense nécessaire à la vie quotidienne."})
Tag.objects.get_or_create(name="Plaisir", defaults={'description': "Dépense non essentielle, liée aux loisirs ou au confort."})
Tag.objects.get_or_create(name="Commun", defaults={'description': "Dépense ou revenu partagé avec un foyer ou un groupe."})
Tag.objects.get_or_create(name="Personnel", defaults={'description': "Dépense ou revenu propre à un individu."})
Tag.objects.get_or_create(name="Vacances", defaults={'description': "Dépense spécifique aux périodes de vacances."})
Tag.objects.get_or_create(name="Imprévu", defaults={'description': "Dépense inattendue ou urgente."})
Tag.objects.get_or_create(name="Investissement", defaults={'description': "Opération visant à générer un rendement futur."})
Tag.objects.get_or_create(name="Transfert", defaults={'description': "Mouvement de fonds entre vos propres comptes."}) # Utile pour marquer les TRF

print(f"Total tags created: {Tag.objects.count()}")
print("Category and Tag population complete.")
