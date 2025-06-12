import os
import shutil
from datetime import datetime
from django.conf import settings
from django.db import transaction as db_transaction
from webapp.models import Transaction, Account
from webapp.importers import BaseTransactionImporter
from .transaction_service import TransactionService
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TransactionImportService:
    """
    Service dédié à l'importation de transactions depuis des fichiers.
    Utilise la base de données dans data/db.sqlite3
    """
    def __init__(self, importer: BaseTransactionImporter):
        self.importer = importer
        
        # Utiliser le dossier data à la racine du projet
        self.data_dir = Path(settings.BASE_DIR) / 'data'
        self.imports_dir = self.data_dir / 'imports'
        
        # Créer les dossiers s'ils n'existent pas
        self.data_dir.mkdir(exist_ok=True)
        self.imports_dir.mkdir(exist_ok=True)
        
        logger.info(f"Service d'importation initialisé - Dossier data: {self.data_dir}")

    def process_import(self, file_path, account, user, column_mapping=None):
        """
        Traite le fichier importé et sauvegarde dans data/db.sqlite3
        """
        imported_count = 0
        transaction_service = TransactionService()

        # Sécurité: S'assurer que le compte appartient à l'utilisateur
        if account.user != user:
            logger.warning(f"Tentative d'importation vers le compte {account.id} par utilisateur {user.username}")
            raise ValueError("Vous n'êtes pas autorisé à importer des transactions vers ce compte.")

        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            logger.error(f"Le fichier {file_path} n'existe pas")
            raise ValueError("Le fichier d'importation est introuvable")

        # Archiver le fichier importé dans data/imports/
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        import_filename = f"{timestamp}_{user.username}_{account.name}_{os.path.basename(file_path)}"
        archived_file_path = self.imports_dir / import_filename
        
        try:
            shutil.copy2(file_path, archived_file_path)
            logger.info(f"Fichier archivé dans {archived_file_path}")
        except Exception as e:
            logger.warning(f"Impossible d'archiver le fichier: {e}")

        # Vérifier que la base de données est accessible
        db_path = self.data_dir / 'db.sqlite3'
        if not db_path.exists():
            logger.warning(f"Base de données non trouvée à {db_path}")
            # La base sera créée automatiquement par Django si nécessaire

        with db_transaction.atomic():
            try:
                logger.info(f"Début de l'importation dans la base de données {db_path}")
                
                # Importer les transactions
                transactions_data, import_errors = self.importer.import_transactions(file_path, account, user)

                # Gérer les erreurs d'importation
                if import_errors:
                    for error in import_errors:
                        logger.warning(f"Erreur d'importation: {error}")

                # Si aucune transaction n'a été extraite, lever une exception
                if not transactions_data:
                    error_msg = "Aucune transaction valide n'a pu être extraite du fichier"
                    logger.error(error_msg)
                    raise ValueError(error_msg)

                # Traiter chaque transaction
                for data in transactions_data:
                    # Filtrer les doublons
                    existing_transaction = Transaction.objects.filter(
                        user=user,
                        date=data['date'],
                        description=data['description'],
                        amount=data['amount'],
                        account=data['account']
                    ).first()

                    if existing_transaction:
                        logger.info(f"Transaction doublon ignorée: {data['description']} le {data['date']}")
                        continue

                    transaction_data_for_service = {
                        'date': data['date'],
                        'description': data['description'],
                        'amount': data['amount'],
                        'account': data['account'],
                        'transaction_type': data.get('transaction_type', 'OUT' if data['amount'] < 0 else 'IN'),
                        'category': data.get('category'),
                        'tags': data.get('tags', []),
                    }

                    transaction_service.create_transaction(transaction_data_for_service, user)
                    imported_count += 1

                logger.info(f"Importation terminée: {imported_count} transactions ajoutées à {db_path}")

            except ValueError as e:
                logger.error(f"Erreur de valeur lors de l'importation: {e}")
                raise e
            except Exception as e:
                logger.critical(f"Erreur inattendue lors de l'importation: {e}")
                raise Exception(f"Erreur lors de l'importation des transactions: {e}")

        return imported_count
