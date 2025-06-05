# webapp/importers/csv_generic.py
import csv
import io
from datetime import datetime
from decimal import Decimal
from .base import BaseTransactionImporter # Importer la classe de base
import logging # Importer le module logging

# Obtenir une instance du logger pour ce module
logger = logging.getLogger(__name__)

class CsvTransactionImporter(BaseTransactionImporter):
    """
    Implémentation concrète de BaseTransactionImporter pour les fichiers CSV génériques,
    nécessitant un mappage de colonnes.
    """
    def import_transactions(self, file_content: str, account, column_mapping: dict) -> list[dict]:
        transactions_data = []
        io_string = io.StringIO(file_content)
        
        reader = csv.DictReader(io_string)
        
        if reader.fieldnames is None:
            logger.error("Le fichier CSV est vide ou son format d'en-tête est invalide.")
            raise ValueError("Le fichier CSV est vide ou son format d'en-tête est invalide.")

        required_internal_fields = ['date', 'description', 'amount']
        
        if not column_mapping:
            logger.error("Le mappage des colonnes est requis pour l'importateur CSV générique.")
            raise ValueError("Le mappage des colonnes est requis pour l'importateur CSV générique.")

        required_csv_columns = [column_mapping.get(field) for field in required_internal_fields if column_mapping.get(field)]
        
        if not all(col in reader.fieldnames for col in required_csv_columns):
            missing_cols = [col for col in required_csv_columns if col not in reader.fieldnames]
            logger.error(
                f"Le fichier CSV ne contient pas toutes les colonnes mappées requises. "
                f"Colonnes manquantes: {', '.join(missing_cols)}. "
                f"Colonnes trouvées dans le fichier: {', '.join(reader.fieldnames)}"
            )
            raise ValueError(
                f"Le fichier CSV ne contient pas toutes les colonnes mappées requises. "
                f"Colonnes manquantes: {', '.join(missing_cols)}. "
                f"Colonnes trouvées dans le fichier: {', '.join(reader.fieldnames)}"
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                date_str = row.get(column_mapping.get('date'))
                description = row.get(column_mapping.get('description'))
                amount_str = row.get(column_mapping.get('amount'))

                if not date_str or not description or not amount_str:
                    logger.warning(f"Ligne {row_num} ignorée (données manquantes): {row}")
                    continue

                try:
                    transaction_date = datetime.strptime(date_str, '%d.%m.%Y').date()
                except ValueError:
                    try:
                        transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        logger.error(f"Format de date invalide pour '{date_str}'. Attendu 'DD.MM.YYYY' ou 'YYYY-MM-DD'.")
                        raise ValueError(f"Format de date invalide pour '{date_str}'. Attendu 'DD.MM.YYYY' ou 'YYYY-MM-DD'.")
                
                amount_str_cleaned = amount_str.replace(',', '.')
                amount = Decimal(amount_str_cleaned)

                transaction_type = 'OUT' if amount < 0 else 'IN'

                transactions_data.append({
                    'date': transaction_date,
                    'description': description,
                    'amount': abs(amount),
                    'account': account,
                    'transaction_type': transaction_type,
                    'category': None
                })
            except ValueError as e:
                logger.error(f"Erreur de parsing de ligne {row_num} CSV: {row} - {e}")
                continue
            except KeyError as e:
                logger.error(f"Erreur de colonne manquante dans la ligne {row_num} CSV: {row} - {e}")
                continue
            except Exception as e:
                logger.critical(f"Erreur inattendue à la ligne {row_num} CSV: {row} - {e}", exc_info=True)
                continue
        return transactions_data
