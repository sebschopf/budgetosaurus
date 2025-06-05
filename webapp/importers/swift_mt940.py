# webapp/importers/swift_mt940.py
from datetime import datetime
from decimal import Decimal
from .base import BaseTransactionImporter # Importer la classe de base
import logging # Importer le module logging

# Obtenir une instance du logger pour ce module
logger = logging.getLogger(__name__)

try:
    import mt940 # Bibliothèque pour le parsing SWIFT MT940
    # import mt940.errors # Commenté pour éviter le problème de Pylance
except ImportError:
    mt940 = None
    logger.warning("La bibliothèque 'mt940' n'est pas installée. L'importation SWIFT MT940 ne sera pas disponible.")


class SwiftMt940TransactionImporter(BaseTransactionImporter):
    """
    Implémentation concrète pour l'importation de fichiers SWIFT MT940/MT942.
    Utilise la bibliothèque 'mt940' pour parser le contenu.
    """
    def import_transactions(self, file_content: str, account, column_mapping: dict = None) -> list[dict]:
        if mt940 is None:
            logger.error("La bibliothèque 'mt940' est requise pour l'importation SWIFT MT940. Veuillez l'installer: pip install mt940")
            raise ImportError("La bibliothèque 'mt940' est requise pour l'importation SWIFT MT940. Veuillez l'installer: pip install mt940")
        
        transactions_data = []
        try:
            logger.debug("Tentative de parsing SWIFT MT940...")
            try:
                statements = mt940.parse(file_content)
            except UnicodeDecodeError:
                logger.debug("Erreur Unicode lors du parsing MT940. Essai avec latin-1...")
                file_content = file_content.encode('latin-1').decode('utf-8')
                statements = mt940.parse(file_content)
            except Exception as e_parse:
                logger.error(f"Erreur de parsing initial par mt940.parse: {e_parse}")
                raise ValueError(f"Le fichier MT940 est malformé ou non valide: {e_parse}")

            logger.debug(f"Nombre de relevés SWIFT trouvés: {len(statements)}")

            if not statements:
                logger.info("Aucun relevé SWIFT trouvé dans le fichier. Le fichier est peut-être vide ou non valide.")
                return []

            for stmt_num, statement in enumerate(statements):
                logger.debug(f"Traitement du relevé SWIFT {stmt_num + 1}...")
                logger.debug(f"Détails du relevé (statement.data): {statement.data}")
                logger.debug(f"Nombre de transactions dans ce relevé: {len(statement.transactions)}")

                if not statement.transactions:
                    logger.info(f"Le relevé {stmt_num + 1} ne contient aucune transaction.")
                    continue

                for tx_num, transaction in enumerate(statement.transactions):
                    logger.debug(f"Traitement de la transaction SWIFT {tx_num + 1}...")
                    logger.debug(f"Données brutes de la transaction: {transaction.data}")

                    transaction_date = transaction.data.get('date') 
                    if not transaction_date:
                        logger.warning(f"Date manquante pour la transaction: {transaction.data}. Ignorée.")
                        continue

                    # date_str = transaction_date.strftime('%Y-%m-%d') # Non utilisé directement, mais peut être utile pour le débogage

                    amount_obj = transaction.data.get('amount')
                    if not amount_obj:
                        logger.warning(f"Montant manquant pour la transaction: {transaction.data}. Ignorée.")
                        continue

                    amount = Decimal(str(amount_obj.amount))
                    
                    # Correction ici: Utiliser amount_obj.is_credit (qui est bien l'attribut de l'objet Amount)
                    transaction_type = 'IN' if amount_obj.is_credit else 'OUT'
                    
                    description = transaction.data.get('transaction_details', '').strip()
                    if not description:
                        description = transaction.data.get('description', '').strip()
                    if not description:
                        description = transaction.data.get('additional_transaction_info', '').strip()
                    if not description:
                        description = transaction.data.get('remittance_information', '').strip()
                    
                    # Logique pour extraire des descriptions plus propres
                    if not description and 'transaction_details' in transaction.data:
                        full_details = transaction.data['transaction_details']
                        if 'Achat ' in full_details:
                            description = full_details.split('Achat ', 1)[1].split('\n')[0].strip()
                        elif 'Crédit ' in full_details:
                            description = full_details.split('Crédit ', 1)[1].split('\n')[0].strip()
                        elif 'Paiement ' in full_details:
                            description = full_details.split('Paiement ', 1)[1].split('\n')[0].strip()
                        elif 'E-banking Ordre à ' in full_details:
                            description = full_details.split('E-banking Ordre à ', 1)[1].split('\n')[0].strip()
                        elif 'Transfert TWINT à ' in full_details:
                            description = full_details.split('Transfert TWINT à ', 1)[1].split('\n')[0].strip()
                        else:
                            description = full_details.split('\n')[0].strip()
                        
                        if description.endswith('No TWINT 92329009'):
                            description = description.replace('No TWINT 92329009', '').strip()
                        if description.endswith('No carte Maestro 83396190'):
                            description = description.replace('No carte Maestro 83396190', '').strip()

                    if not description:
                        description = "Description non trouvée (MT940)"

                    logger.debug(f"Date: '{transaction_date}', Montant: '{amount}', Type: '{transaction_type}', Description Finale: '{description}'")

                    if not all([transaction_date, amount, transaction_type]):
                        logger.warning(f"Transaction MT940 ignorée (données manquantes après parsing): {transaction.data}")
                        continue

                    transactions_data.append({
                        'date': transaction_date,
                        'description': description,
                        'amount': abs(amount),
                        'account': account,
                        'transaction_type': transaction_type,
                        'category': None
                    })
                    logger.debug(f"Transaction MT940 ajoutée à la liste: {description} {amount} {transaction_type}")

            logger.debug(f"Nombre total de transactions MT940 prêtes à être importées: {len(transactions_data)}")
            return transactions_data
        except ValueError as e:
            logger.error(f"ERREUR SWIFT (ValueError): {e}")
            raise
        except Exception as e:
            logger.critical(f"ERREUR INATTENDUE SWIFT: {e}", exc_info=True)
            raise ValueError(f"Une erreur inattendue est survenue lors du parsing SWIFT MT940: {e}. Assurez-vous du format du fichier.")
