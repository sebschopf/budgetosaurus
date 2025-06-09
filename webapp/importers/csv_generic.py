# webapp/importers/csv_generic.py
from datetime import datetime
import csv
from decimal import Decimal, InvalidOperation # pour gérer les erreurs de conversion décimales

from django.db import transaction # Pour s'assurer que l'importation est atomique
from django.utils.translation import gettext_lazy as _ # Pour l'internationalisation

from webapp.models import Transaction, Category, Account
from .base import BaseTransactionImporter

class CsvGenericImporter(BaseTransactionImporter):
    """
    Importateur générique pour les fichiers CSV.
    Configurez les colonnes attendues via self.config.
    """
    def __init__(self, config):
        """
        Initialise l'importateur avec une configuration spécifique pour les colonnes CSV.
        """
        super().__init__()
        self.config = config # La configuration doit définir 'date_column_index', 'description_column_index', etc.

    def import_transactions(self, file_path, account, user):
        """
        Importe les transactions à partir d'un fichier CSV.
        """
        self.errors = [] # Réinitialiser les erreurs pour chaque importation
        imported_transactions_count = 0
        
        # Utilisez transaction.atomic pour s'assurer que toutes les transactions sont importées
        # ou qu'aucune ne l'est si une erreur survient.
        with transaction.atomic():
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # Optionnel : sauter les lignes d'en-tête si configuré
                for _ in range(self.config.get('header_rows', 0)):
                    next(reader)

                for i, row in enumerate(reader):
                    line_num = i + 1 + self.config.get('header_rows', 0) # Numéro de ligne pour les messages d'erreur
                    if not row: # Ignorer les lignes vides
                        continue
                    
                    transaction_obj = self.process_row(row, account, user)
                    if transaction_obj:
                        imported_transactions_count += 1
                    else:
                        # Si process_row renvoie None, cela signifie une erreur a été ajoutée
                        # et nous devons peut-être annuler la transaction atomique
                        # ou simplement continuer en fonction de la stratégie d'erreur.
                        # Ici, nous continuons pour collecter toutes les erreurs.
                        pass
        
        return imported_transactions_count, self.errors

    def process_row(self, row, account, user):
        """
        Traite une seule ligne du fichier CSV et crée/met à jour une transaction.
        """
        try:
            # Récupérer les indices de colonne depuis la configuration
            date_col_idx = self.config['date_column_index']
            description_col_idx = self.config['description_column_index']
            amount_col_idx = self.config['amount_column_index']
            transaction_type_col_idx = self.config.get('transaction_type_column_index') # Optionnel

            # Extraire les données en toute sécurité
            date_str = row[date_col_idx].strip()
            description = row[description_col_idx].strip()
            amount_str = row[amount_col_idx].replace(',', '.').strip() # Gérer les virgules comme séparateur décimal

            
            # Le champ 'date' de Transaction est un DateField, pas un DateTimeField.
            # Cela signifie qu'il stocke uniquement la date (année, mois, jour) et n'est pas sensible aux fuseaux horaires.
            # Nous devons juste nous assurer que nous parsons la chaîne en un objet Python `date`.
            # Si le format de date dans votre CSV inclut l'heure, .date() l'ignorera.
            # Le format de date est défini dans self.config['date_format'] (ex: '%Y-%m-%d')
            parsed_datetime = datetime.strptime(date_str, self.config['date_format'])
            transaction_date = parsed_datetime.date() # Extrait uniquement la partie date

            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                self.errors.append(_(f"Ligne {row}: Montant invalide '{amount_str}'. Doit être un nombre valide."))
                return None

            # Déterminer le type de transaction (IN/OUT)
            # Si un indice de colonne de type de transaction est fourni, utilisez-le.
            # Sinon, déduisez le type en fonction du signe du montant.
            transaction_type = 'OUT' # Valeur par défaut
            if transaction_type_col_idx is not None:
                type_str = row[transaction_type_col_idx].strip().upper()
                if type_str in ['IN', 'INCOME', 'CREDIT']:
                    transaction_type = 'IN'
                elif type_str in ['OUT', 'EXPENSE', 'DEBIT']:
                    transaction_type = 'OUT'
            else:
                if amount > 0:
                    transaction_type = 'IN'
                else:
                    transaction_type = 'OUT'
                    amount = abs(amount) # Stocker le montant des dépenses comme un nombre positif

            # Chercher une transaction existante pour éviter les doublons
            # Critères de déduplication : même compte, même date, même montant, même description
            existing_transaction = Transaction.objects.filter(
                user=user,
                account=account,
                date=transaction_date,
                amount=amount if transaction_type == 'IN' else -amount, # Comparer le montant stocké
                description=description
            ).first()

            if existing_transaction:
                self.warnings.append(_(f"Transaction existante trouvée et ignorée (doublon potentiel): {description} le {date_str} - Montant: {amount}"))
                return None

            # Créer la nouvelle transaction
            transaction = Transaction.objects.create(
                user=user,
                date=transaction_date,
                description=description,
                amount=amount if transaction_type == 'IN' else -amount, # Stocker les dépenses comme négatives
                category=None, # La catégorie sera assignée plus tard ou par règles
                account=account,
                transaction_type=transaction_type
            )
            return transaction

        except IndexError:
            self.errors.append(_(f"Ligne {row}: Colonne manquante ou indice invalide dans la configuration de l'importateur. Vérifiez les indices de colonne."))
            return None
        except ValueError as e:
            self.errors.append(_(f"Ligne {row}: Erreur de parsing des données: {e}"))
            return None
        except Exception as e:
            self.errors.append(_(f"Ligne {row}: Une erreur inattendue est survenue lors du traitement: {e}"))
            return None

