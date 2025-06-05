# webapp/importers/csv_raiffeisen.py
import csv
import io
from datetime import datetime
from decimal import Decimal
from .base import BaseTransactionImporter # Importer la classe de base
import logging # Importer le module logging

# Obtenir une instance du logger pour ce module
logger = logging.getLogger(__name__)

class RaiffeisenCsvTransactionImporter(BaseTransactionImporter):
    """
    Implémentation concrète pour les fichiers CSV de Raiffeisen.
    Gère spécifiquement les colonnes 'Débit' et 'Crédit' séparées.
    """
    def import_transactions(self, file_content: str, account, column_mapping: dict = None) -> list[dict]:
        transactions_data = []
        io_string = io.StringIO(file_content)
        reader = csv.DictReader(io_string)

        if reader.fieldnames is None:
            logger.error("Le fichier CSV Raiffeisen est vide ou son format d'en-tête est invalide.")
            raise ValueError("Le fichier CSV Raiffeisen est vide ou son format d'en-tête est invalide.")

        # Noms de colonnes spécifiques à Raiffeisen (à adapter si différents dans votre export)
        DATE_COL = 'Date comptable'
        DESCRIPTION_COL = 'Libellé'
        DEBIT_COL = 'Débit'
        CREDIT_COL = 'Crédit'

        if not all(col in reader.fieldnames for col in [DATE_COL, DESCRIPTION_COL]):
            logger.error(
                f"Le fichier CSV Raiffeisen doit contenir les colonnes '{DATE_COL}' et '{DESCRIPTION_COL}'. "
                f"Colonnes trouvées: {', '.join(reader.fieldnames)}"
            )
            raise ValueError(
                f"Le fichier CSV Raiffeisen doit contenir les colonnes '{DATE_COL}' et '{DESCRIPTION_COL}'. "
                f"Colonnes trouvées: {', '.join(reader.fieldnames)}"
            )
        if not (DEBIT_COL in reader.fieldnames or CREDIT_COL in reader.fieldnames):
            logger.error(
                f"Le fichier CSV Raiffeisen doit contenir au moins une des colonnes '{DEBIT_COL}' ou '{CREDIT_COL}'."
            )
            raise ValueError(
                f"Le fichier CSV Raiffeisen doit contenir au moins une des colonnes '{DEBIT_COL}' ou '{CREDIT_COL}'."
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                date_str = row.get(DATE_COL)
                description = row.get(DESCRIPTION_COL)
                debit_str = row.get(DEBIT_COL, '').strip()
                credit_str = row.get(CREDIT_COL, '').strip()

                if not date_str or not description:
                    logger.warning(f"Ligne {row_num} ignorée (date ou description manquante): {row}")
                    continue
                
                try:
                    transaction_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                except ValueError:
                    try:
                        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        logger.error(f"Format de date invalide pour '{date_str}' à la ligne {row_num}. Attendu 'DD.MM.YYYY' ou 'YYYY-MM-DD'.")
                        raise ValueError(f"Format de date invalide pour '{date_str}' à la ligne {row_num}. Attendu 'DD.MM.YYYY' ou 'YYYY-MM-DD'.")

                amount = Decimal(0)
                transaction_type = ''

                if debit_str and debit_str != '0' and debit_str != '-':
                    amount_cleaned = debit_str.replace(',', '.')
                    amount = Decimal(amount_cleaned)
                    transaction_type = 'OUT'
                elif credit_str and credit_str != '0' and credit_str != '-':
                    amount_cleaned = credit_str.replace(',', '.')
                    amount = Decimal(amount_cleaned)
                    transaction_type = 'IN'
                else:
                    logger.warning(f"Ligne {row_num} ignorée (montant invalide ou vide): {row}")
                    continue

                transactions_data.append({
                    'date': transaction_date,
                    'description': description,
                    'amount': amount,
                    'account': account,
                    'transaction_type': transaction_type,
                    'category': None
                })
            except ValueError as e:
                logger.error(f"Erreur de parsing de ligne {row_num} CSV Raiffeisen: {row} - {e}")
                continue
            except KeyError as e:
                logger.error(f"Erreur de colonne manquante dans la ligne {row_num} CSV Raiffeisen: {row} - {e}")
                continue
            except Exception as e:
                logger.critical(f"Erreur inattendue à la ligne {row_num} CSV Raiffeisen: {row} - {e}", exc_info=True)
                continue
        return transactions_data
