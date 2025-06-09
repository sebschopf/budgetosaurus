# webapp/importers/csv_raiffeisen.py
from datetime import datetime
import csv
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from webapp.models import Transaction, Category, Account
from .base import BaseTransactionImporter

class CsvRaiffeisenImporter(BaseTransactionImporter):
    """
    Importateur spécifique pour les fichiers CSV de Raiffeisen Bank.
    Les indices de colonne sont codés en dur car le format de Raiffeisen est connu.
    """
    def __init__(self):
        """
        Initialise l'importateur avec les indices de colonne spécifiques à Raiffeisen.
        """
        super().__init__()
        # Ces indices sont basés sur un format CSV typique de Raiffeisen.
        #  ajuster en fonction de l'exportation réelle de la banque.
        self.config = {
            'header_rows': 1, # Nombre de lignes d'en-tête à sauter
            'date_column_index': 0, # Ex: "Buchungsdatum"
            'description_column_index': 5, # Ex: "Buchungstext" ou "Verwendungszweck"
            'amount_column_index': 3, # Ex: "Betrag" (peut être "Soll" ou "Haben" séparément, à adapter)
            'date_format': '%d.%m.%Y', # Format de date typique (jour.mois.année)
            # Raiffeisen utilise souvent des colonnes séparées pour débit et crédit,
            # ou un montant unique avec un signe.
            # Adapter la logique 'process_row' si des colonnes Soll/Haben sont utilisées.
        }

    def import_transactions(self, file_path, account, user):
        """
        Importe les transactions à partir d'un fichier CSV Raiffeisen.
        """
        self.errors = []
        self.warnings = [] # Initialiser la liste des avertissements
        imported_transactions_count = 0
        
        with transaction.atomic():
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile, delimiter=';') # Utiliser le point-virgule comme délimiteur typique

                # Sauter les lignes d'en-tête
                for _ in range(self.config.get('header_rows', 0)):
                    next(reader)

                for i, row in enumerate(reader):
                    line_num = i + 1 + self.config.get('header_rows', 0)
                    if not row or len(row) < max(self.config.values()) + 1: # Vérifier la validité de la ligne
                        if row: # Seulement si la ligne n'est pas complètement vide
                            self.errors.append(_(f"Ligne {line_num}: Ligne incomplète ou invalide. Ignorée: {row}"))
                        continue
                    
                    transaction_obj = self.process_row(row, account, user, line_num)
                    if transaction_obj:
                        imported_transactions_count += 1
        
        return imported_transactions_count, self.errors + self.warnings # Retourner erreurs et avertissements

    def process_row(self, row, account, user, line_num):
        """
        Traite une seule ligne du fichier CSV de Raiffeisen et crée une transaction.
        """
        try:
            date_str = row[self.config['date_column_index']].strip()
            description = row[self.config['description_column_index']].strip()
            amount_str = row[self.config['amount_column_index']].replace(',', '.').strip() # Gérer les virgules


            # Le champ 'date' de Transaction est un DateField, pas un DateTimeField.
            # Nous parsons la chaîne en un objet datetime, puis nous extrayons seulement la date.
            try:
                parsed_datetime = datetime.strptime(date_str, self.config['date_format'])
                transaction_date = parsed_datetime.date() # Extrait uniquement la partie date
            except ValueError:
                self.errors.append(_(f"Ligne {line_num}: Format de date invalide '{date_str}'. Attendu: '{self.config['date_format']}'."))
                return None


            try:
                amount = Decimal(amount_str)
            except InvalidOperation:
                self.errors.append(_(f"Ligne {line_num}: Montant invalide '{amount_str}'. Doit être un nombre valide."))
                return None
            
            # Déterminer le type de transaction basé sur le signe du montant
            transaction_type = 'OUT'
            if amount > 0:
                transaction_type = 'IN'
            else:
                amount = abs(amount) # Stocker le montant des dépenses comme un nombre positif

            # Vérifier l'existence de doublons
            existing_transaction = Transaction.objects.filter(
                user=user,
                account=account,
                date=transaction_date,
                amount=amount if transaction_type == 'IN' else -amount, # Comparer le montant stocké
                description=description
            ).first()

            if existing_transaction:
                self.warnings.append(_(f"Ligne {line_num}: Transaction existante trouvée et ignorée (doublon potentiel): {description} le {date_str} - Montant: {amount}."))
                return None

            # Créer la transaction
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
            self.errors.append(_(f"Ligne {line_num}: Colonne manquante ou indice invalide dans la configuration de l'importateur. Vérifiez les indices de colonne ou la structure du fichier."))
            return None
        except Exception as e:
            self.errors.append(_(f"Ligne {line_num}: Une erreur inattendue est survenue lors du traitement: {e} - Contenu: {row}"))
            return None

