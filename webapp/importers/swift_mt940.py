# webapp/importers/swift_mt940.py
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from mt940.models import Transaction as MT940Transaction # transaction MT940
from webapp.models import Transaction, Account, Category # webapp
from .base import BaseTransactionImporter

class SwiftMt940Importer(BaseTransactionImporter):
    """
    Importateur pour les fichiers SWIFT MT940.
    Utilise la bibliothèque `mt940` pour parser le fichier.
    """
    def __init__(self):
        super().__init__()

    def import_transactions(self, file_path, account, user):
        """
        Importe les transactions à partir d'un fichier SWIFT MT940.
        """
        self.errors = []
        self.warnings = []
        imported_transactions_count = 0

        try:
            # Charger le fichier MT940
            with open(file_path, 'r', encoding='utf-8') as f:
                # La bibliothèque mt940 renvoie un objet Statement ou un dictionnaire de Statement
                statements = MT940Transaction.parse(f)

            # Si c'est un dictionnaire, parcourir les valeurs (statements)
            if isinstance(statements, dict):
                statements_list = statements.values()
            else:
                statements_list = [statements] # Si c'est un seul Statement, le mettre dans une liste

            with transaction.atomic():
                for statement in statements_list:
                    for entry in statement.data:
                        # Extraire les données nécessaires de chaque entrée MT940
                        # Les dates dans mt940.models.Transaction sont déjà des objets date ou datetime
                        # Nous devons nous assurer qu'ils sont des objets `date` si le champ est DateField

                        # date est un datetime.date object from mt940, direct mapping to Django DateField
                        transaction_date = entry.valuta_date or entry.date # Utilise valuta_date si disponible, sinon date

                        description = entry.description.strip()
                        amount = Decimal(entry.amount.amount) # L'amount est déjà un Decimal

                        # Déterminer le type de transaction
                        transaction_type = 'OUT' if amount < 0 else 'IN'
                        amount = abs(amount) # Stocker le montant comme positif, le signe est géré par transaction_type dans le modèle

                        # Vérifier l'existence de doublons
                        existing_transaction = Transaction.objects.filter(
                            user=user,
                            account=account,
                            date=transaction_date,
                            amount=amount if transaction_type == 'IN' else -amount,
                            description=description
                        ).first()

                        if existing_transaction:
                            self.warnings.append(_(f"Transaction existante trouvée et ignorée (doublon potentiel): {description} le {transaction_date} - Montant: {amount}."))
                            continue

                        # Créer la transaction
                        Transaction.objects.create(
                            user=user,
                            date=transaction_date,
                            description=description,
                            amount=amount if transaction_type == 'IN' else -amount,
                            category=None,
                            account=account,
                            transaction_type=transaction_type
                        )
                        imported_transactions_count += 1
        except FileNotFoundError:
            self.errors.append(_("Fichier non trouvé. Veuillez vérifier le chemin."))
        except InvalidOperation:
            self.errors.append(_("Erreur de conversion de montant dans le fichier MT940."))
        except Exception as e:
            self.errors.append(_(f"Erreur lors de l'importation du fichier MT940: {e}"))

        return imported_transactions_count, self.errors + self.warnings

