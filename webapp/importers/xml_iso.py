import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)

class XmlIsoImporter:
    """
    Importateur pour les fichiers XML au format ISO 20022 camt.053
    """
    
    def __init__(self):
        self.namespace = {'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.08'}
    
    def import_transactions(self, file_path, account, user):
        """
        Importe les transactions depuis un fichier XML ISO 20022
        
        Args:
            file_path: Chemin vers le fichier XML
            account: Compte bancaire de destination
            user: Utilisateur propriétaire des transactions
            
        Returns:
            tuple: (liste des transactions, liste d'erreurs)
        """
        transactions_data = []
        errors = []
        
        try:
            # Analyser le fichier XML
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Gérer le namespace correctement
            if root.tag.startswith('{'):
                ns_uri = root.tag[1:].split('}')[0]
                self.namespace = {'ns': ns_uri}
                logger.info(f"Namespace détecté: {ns_uri}")
            
            # Trouver toutes les entrées de transaction
            entries = root.findall('.//ns:Ntry', self.namespace)
            
            if not entries:
                logger.warning(f"Aucune entrée de transaction trouvée dans le fichier XML")
                errors.append("Aucune entrée de transaction trouvée dans le fichier XML")
                return transactions_data, errors
            
            logger.info(f"Nombre d'entrées trouvées: {len(entries)}")
            
            for entry in entries:
                try:
                    # Extraire les données de la transaction
                    transaction_data = self._extract_transaction_data(entry, account, user)
                    
                    if transaction_data:
                        transactions_data.append(transaction_data)
                    
                except Exception as e:
                    error_msg = f"Erreur lors de l'extraction des données de transaction: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
            
            logger.info(f"Importation terminée: {len(transactions_data)} transactions extraites")
            
        except ET.ParseError as e:
            error_msg = f"Erreur de parsing XML: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Erreur inattendue lors de l'importation: {str(e)}"
            logger.error(error_msg, exc_info=True)
            errors.append(error_msg)
        
        return transactions_data, errors
    
    def _extract_transaction_data(self, entry, account, user):
        """
        Extrait les données d'une entrée de transaction
        """
        try:
            # Montant et devise
            amount_elem = entry.find('.//ns:Amt', self.namespace)
            if amount_elem is None:
                logger.warning("Élément montant non trouvé")
                return None
                
            amount = Decimal(amount_elem.text)
            currency = amount_elem.get('Ccy', 'CHF')
            
            # Type de transaction (débit/crédit)
            credit_debit = entry.find('.//ns:CdtDbtInd', self.namespace)
            if credit_debit is None:
                logger.warning("Indicateur débit/crédit non trouvé")
                return None
                
            transaction_type = 'IN' if credit_debit.text == 'CRDT' else 'OUT'
            
            # Si c'est un débit, le montant doit être négatif
            if transaction_type == 'OUT':
                amount = -amount
            
            # Date de la transaction
            booking_date_elem = entry.find('.//ns:BookgDt/ns:Dt', self.namespace)
            if booking_date_elem is None:
                logger.warning("Date de comptabilisation non trouvée")
                return None
                
            date_str = booking_date_elem.text
            transaction_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            # Description de la transaction
            description = ""
            addtl_info = entry.find('.//ns:AddtlNtryInf', self.namespace)
            if addtl_info is not None and addtl_info.text:
                description = addtl_info.text.strip()
            
            # Si pas de description dans AddtlNtryInf, essayer d'autres champs
            if not description:
                # Essayer le code de transaction bancaire
                bank_tx_code = entry.find('.//ns:BkTxCd/ns:Prtry/ns:Cd', self.namespace)
                if bank_tx_code is not None and bank_tx_code.text:
                    description = f"Transaction bancaire - Code: {bank_tx_code.text}"
            
            # Référence de la transaction
            reference = ""
            acct_svcr_ref = entry.find('.//ns:AcctSvcrRef', self.namespace)
            if acct_svcr_ref is not None and acct_svcr_ref.text:
                reference = acct_svcr_ref.text.strip()
            
            # Créer le dictionnaire de données de transaction
            transaction_data = {
                'date': transaction_date,
                'description': description or f"Transaction du {transaction_date}",
                'amount': amount,
                'account': account,
                'transaction_type': transaction_type,
                'reference': reference,
            }
            
            return transaction_data
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction des données: {str(e)}", exc_info=True)
            return None
