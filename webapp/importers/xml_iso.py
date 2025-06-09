# webapp/importers/xml_iso.py
from datetime import datetime
from decimal import Decimal, InvalidOperation
import xml.etree.ElementTree as ET

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from webapp.models import Transaction, Account, Category
from .base import BaseTransactionImporter

class XmlIsoImporter(BaseTransactionImporter):
    """
    Importateur pour les fichiers XML au format ISO 20022 (par exemple, camt.053).
    """
    def __init__(self):
        super().__init__()

    def import_transactions(self, file_path, account, user):
        """
        Importe les transactions à partir d'un fichier XML ISO 20022.
        """
        self.errors = []
        self.warnings = []
        imported_transactions_count = 0

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Les namespaces peuvent varier, il est donc préférable de les gérer dynamiquement ou de les ignorer si possible
            # Pour simplifier, chercher des éléments sans préfixe de namespace pour les noms courants
            # ou utiliser le namespace complet si c'est constant (ex: urn:iso:std:iso:20022:tech:xsd:camt.053.001.02)
            # Une approche plus robuste serait de parser le namespace du root et de l'utiliser.
            
            # Rechercher les entrées de relevé de compte (Ntry)
            # Exemple de chemin XPath pour les transactions (à adapter si nécessaire)
            # Il est crucial de connaître le namespace correct ou de l'ignorer.
            # Dans la plupart des cas, les fichiers camt utilisent un namespace par défaut.
            # Si le namespace est présent, utilisez {namespace_uri}TagName
            # Ou utilisez un caractère joker pour le namespace local-name()='TagName'
            
            # Exemple générique: Trouver toutes les "Ntry" qui représentent une transaction
            # Note: cela peut nécessiter une adaptation si le fichier XML utilise des namespaces complexes.
            # Un namespace typique pour camt.053 est 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'
            # Pour l'exemple, nous allons chercher des éléments sans namespace défini,
            # ou vous devrez déterminer le namespace du document.
            
            # Pour une approche générique qui ignore le namespace (si le tag est unique)
            # Ou spécifiez un namespace si vous le connaissez (ex: '{urn:iso:std:iso:20022:tech:xsd:camt.053.001.02}Ntry')
            # Ou utilisez un XPath plus robuste: .//*[local-name()='Ntry']
            
            # Supposons un chemin simplifié pour l'exemple. Adaptez selon votre XML réel.
            # Si le XML a un namespace par défaut, vous devrez l'utiliser :
            # namespace = {'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'}
            # entries = root.findall('.//ns:Ntry', namespace)

            # Une approche plus simple pour trouver tous les éléments 'Ntry' quel que soit leur namespace
            entries = root.findall(".//*[local-name()='Ntry']")

            with transaction.atomic():
                for entry in entries:
                    # Date de la transaction (BookgDt ou ValDt)
                    # Cherche la date de comptabilisation ou la date de valeur
                    date_element = entry.find(".//*[local-name()='BookgDt']/*[local-name()='Dt']") or \
                                   entry.find(".//*[local-name()='ValDt']/*[local-name()='Dt']")
                    date_str = date_element.text if date_element is not None else None

                    # Montant
                    amt_element = entry.find(".//*[local-name()='Amt']")
                    amount_str = amt_element.text if amt_element is not None else None
                    
                    # Débit/Crédit (CdtDbtInd)
                    c_d_ind_element = entry.find(".//*[local-name()='CdtDbtInd']")
                    credit_debit_indicator = c_d_ind_element.text if c_d_ind_element is not None else None

                    # Description (NtryDtls -> TxDtls -> RmtInf -> Strd -> RfrdDocInf -> Nb) ou Narr
                    # La description peut être dans plusieurs endroits dans ISO 20022
                    # Voici un exemple, à adapter selon le champ le plus pertinent pour vous.
                    # On peut chercher dans Purp, AddtlNtryInf, ou RmtInf/Ustrd/Strd/RfrdDocInf/Nb/Issr
                    
                    # Tentons de trouver une description commune:
                    description_element = entry.find(".//*[local-name()='AddtlNtryInf']") or \
                                          entry.find(".//*[local-name()='RemittanceInformation']/*[local-name()='Unstructured']")
                    description = description_element.text.strip() if description_element is not None and description_element.text else "Description non disponible"

                    if not all([date_str, amount_str, credit_debit_indicator]):
                        self.warnings.append(_(f"Skipping incomplete transaction entry: Date='{date_str}', Amount='{amount_str}', CdtDbtInd='{credit_debit_indicator}'"))
                        continue

                    # Le champ 'date' de Transaction est un DateField, pas un DateTimeField.
                    # Les dates ISO 20022 sont souvent au format YYYY-MM-DD
                    try:
                        parsed_datetime = datetime.strptime(date_str, '%Y-%m-%d')
                        transaction_date = parsed_datetime.date() # Extrait uniquement la partie date
                    except ValueError:
                        self.errors.append(_(f"Format de date XML invalide '{date_str}'. Attendu: 'YYYY-MM-DD'."))
                        continue # Passe à l'entrée suivante
                    
                    try:
                        amount = Decimal(amount_str)
                    except InvalidOperation:
                        self.errors.append(_(f"Montant XML invalide '{amount_str}'."))
                        continue

                    # Appliquer le signe basé sur l'indicateur débit/crédit
                    transaction_type = 'OUT'
                    if credit_debit_indicator == 'CRDT': # Crédit = Revenu
                        transaction_type = 'IN'
                    elif credit_debit_indicator == 'DBIT': # Débit = Dépense
                        pass # transaction_type reste 'OUT'

                    amount = abs(amount) # Toujours stocker le montant absolu

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
            self.errors.append(_("Fichier XML non trouvé. Veuillez vérifier le chemin."))
        except ET.ParseError as e:
            self.errors.append(_(f"Erreur de parsing XML: {e}. Le fichier n'est peut-être pas un XML valide."))
        except Exception as e:
            self.errors.append(_(f"Erreur inattendue lors de l'importation du fichier XML: {e}"))

        return imported_transactions_count, self.errors + self.warnings

