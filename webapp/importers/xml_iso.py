# webapp/importers/xml_iso.py
from datetime import datetime
from decimal import Decimal
from .base import BaseTransactionImporter
import logging # Importer le module logging

# Obtenir une instance du logger pour ce module
logger = logging.getLogger(__name__)

try:
    from lxml import etree
except ImportError:
    etree = None
    logger.warning("La bibliothèque 'lxml' n'est pas installée. L'importation XML ISO ne sera pas disponible.")

class XmlIsoTransactionImporter(BaseTransactionImporter):
    """
    Importateur pour les fichiers XML ISO 20022 (camt.053.001.08).
    Adapte le parsing aux chemins XPath spécifiques de ce format, y compris les opérations groupées.
    Extrait des détails plus précis sur la description et les parties liées (nom, IBAN).
    """
    def import_transactions(self, file_content: str, account, column_mapping: dict = None) -> list[dict]:
        if etree is None:
            logger.error("La bibliothèque 'lxml' est requise pour l'importation XML ISO. Veuillez l'installer: pip install lxml")
            raise ImportError("La bibliothèque 'lxml' est requise pour l'importation XML ISO. Veuillez l'installer: pip install lxml")
        
        transactions_data = []
        try:
            logger.debug("Tentative de parsing XML...")
            try:
                # Essai de décodage avec utf-8, puis latin-1 si échec
                root = etree.fromstring(file_content.encode('utf-8'))
            except Exception:
                logger.debug("Erreur Unicode lors du parsing XML avec utf-8. Essai avec latin-1...")
                root = etree.fromstring(file_content.encode('latin-1'))
            
            logger.debug(f"Racine XML trouvée: {root.tag}")
            
            ns = {'ns': 'urn:iso:std:iso:20022:tech:xsd:camt.053.001.08'} 

            statements = root.xpath('/ns:Document/ns:BkToCstmrStmt/ns:Stmt', namespaces=ns)
            logger.debug(f"Nombre de relevés (Stmt) trouvés: {len(statements)}")

            if not statements:
                statements = root.xpath('//ns:Stmt', namespaces=ns)
                logger.debug(f"Aucune balise 'Stmt' trouvée au chemin direct. Tentative générique: {len(statements)}")
                if not statements:
                    logger.error("Aucune balise 'Stmt' trouvée dans le fichier XML. Vérifiez le namespace et la structure.")
                    raise ValueError("Aucune balise 'Stmt' trouvée dans le fichier XML. Vérifiez le namespace et la structure.")

            for stmt in statements:
                iban_node = stmt.xpath('./ns:Acct/ns:Id/ns:IBAN/text()', namespaces=ns)
                statement_iban = iban_node[0] if iban_node else 'N/A'
                logger.debug(f"Traitement du relevé pour IBAN: {statement_iban}")

                entries = stmt.xpath('.//ns:Ntry', namespaces=ns)
                logger.debug(f"Nombre d'entrées (Ntry) trouvées dans ce relevé: {len(entries)}")

                if not entries:
                    logger.info(f"Aucune balise <Ntry> trouvée dans le relevé pour IBAN {statement_iban}. Pas de transactions à importer.")
                    continue

                for entry_num, entry in enumerate(entries):
                    entry_bookg_date_node = entry.xpath('./ns:BookgDt/ns:Dt/text()', namespaces=ns)
                    entry_bookg_date_str = entry_bookg_date_node[0] if entry_bookg_date_node else None

                    batch_details = entry.xpath('./ns:NtryDtls/ns:Btch', namespaces=ns)
                    
                    if batch_details:
                        logger.debug(f"Opération groupée (Batch) détectée pour Ntry {entry_num + 1}. Traitement des TxDtls...")
                        tx_dtls_list = entry.xpath('./ns:NtryDtls/ns:TxDtls', namespaces=ns)
                        if not tx_dtls_list:
                            logger.warning(f"Batch détecté mais aucune TxDtls trouvée pour Ntry {entry_num + 1}. Ignoré.")
                            continue

                        for tx_dtls_num, tx_dtls in enumerate(tx_dtls_list):
                            amount_node = tx_dtls.xpath('./ns:Amt/text()', namespaces=ns)
                            if not amount_node:
                                amount_node = tx_dtls.xpath('./ns:Amt/ns:InstdAmt/text()', namespaces=ns)
                            amount_str = amount_node[0] if amount_node else None

                            CdtDbtInd_node = tx_dtls.xpath('./ns:CdtDbtInd/text()', namespaces=ns)
                            CdtDbtInd = CdtDbtInd_node[0] if CdtDbtInd_node else None

                            # --- LOGIQUE DE DESCRIPTION PRÉCISE POUR TxDtls (transactions individuelles dans un batch) ---
                            main_description_parts = []
                            secondary_details = [] # Initialisation pour chaque transaction individuelle
                            
                            # 1. Nom du Débiteur/Créditeur (Partie liée) - souvent le plus important pour l'identification
                            dbtr_name_node = tx_dtls.xpath('.//ns:RltdPties/ns:Dbtr/ns:Pty/ns:Nm/text()', namespaces=ns)
                            cdtr_name_node = tx_dtls.xpath('.//ns:RltdPties/ns:Cdtr/ns:Pty/ns:Nm/text()', namespaces=ns)

                            related_party_name = None
                            if CdtDbtInd == 'DBIT' and cdtr_name_node: # Si c'est un débit, le créditeur est la contrepartie
                                related_party_name = cdtr_name_node[0].strip()
                            elif CdtDbtInd == 'CRDT' and dbtr_name_node: # Si c'est un crédit, le débiteur est la contrepartie
                                related_party_name = dbtr_name_node[0].strip()
                            
                            if related_party_name:
                                main_description_parts.append(related_party_name)

                            # 2. Informations de remise non structurées (Ustrd) - Libellé de l'opération
                            remittance_ustrd_node = tx_dtls.xpath('.//ns:RmtInf/ns:Ustrd/text()', namespaces=ns)
                            if remittance_ustrd_node:
                                ustrd_text = remittance_ustrd_node[0].strip()
                                if ustrd_text and ustrd_text not in main_description_parts:
                                    main_description_parts.append(ustrd_text)

                            # 3. Référence de paiement structurée (Ref) ou AddtlRmtInf
                            remittance_strd_ref_node = tx_dtls.xpath('.//ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref/text()', namespaces=ns)
                            if remittance_strd_ref_node:
                                secondary_details.append(f"Ref: {remittance_strd_ref_node[0].strip()}")
                            
                            remittance_addtl_strd_node = tx_dtls.xpath('.//ns:RmtInf/ns:Strd/ns:AddtlRmtInf/text()', namespaces=ns)
                            if remittance_addtl_strd_node:
                                secondary_details.append(remittance_addtl_strd_node[0].strip())

                            # 4. Bank Transaction Code (Prtry/Nm ou Cd)
                            bk_tx_cd_node_nm = tx_dtls.xpath('.//ns:BkTxCd/ns:Prtry/ns:Nm/text()', namespaces=ns)
                            if not bk_tx_cd_node_nm: # Fallback pour Cd si Nm n'existe pas
                                bk_tx_cd_node_nm = tx_dtls.xpath('.//ns:BkTxCd/ns:Prtry/ns:Cd/text()', namespaces=ns)
                            if bk_tx_cd_node_nm:
                                secondary_details.append(f"Code Tx: {bk_tx_cd_node_nm[0].strip()}")

                            # 5. IBAN de la contrepartie
                            counterparty_iban = None
                            dbtr_iban_node = tx_dtls.xpath('.//ns:RltdPties/ns:DbtrAcct/ns:Id/ns:IBAN/text()', namespaces=ns)
                            cdtr_iban_node = tx_dtls.xpath('.//ns:RltdPties/ns:CdtrAcct/ns:Id/ns:IBAN/text()', namespaces=ns)
                            
                            if CdtDbtInd == 'DBIT' and cdtr_iban_node:
                                counterparty_iban = cdtr_iban_node[0].strip()
                            elif CdtDbtInd == 'CRDT' and dbtr_iban_node:
                                counterparty_iban = dbtr_iban_node[0].strip()
                            
                            if counterparty_iban:
                                secondary_details.append(f"IBAN: {counterparty_iban}")

                            # Concaténer les parties de la description
                            description = " - ".join(filter(None, main_description_parts))
                            if secondary_details:
                                description += f" ({' ; '.join(filter(None, secondary_details))})"
                            
                            if not description.strip():
                                description = "Description non trouvée (TxDtls)"
                            # --- FIN LOGIQUE DE DESCRIPTION PRÉCISE ---

                            date_str_final = entry_bookg_date_str 

                            # MODIFIÉ: Vérification de la validité de date_str_final
                            if not date_str_final:
                                logger.warning(f"TxDtls ignorée (date manquante): Montant={amount_str}, CdtDbtInd={CdtDbtInd}")
                                continue # Ignorer cette transaction si la date est manquante

                            if not all([amount_str, CdtDbtInd]):
                                logger.warning(f"TxDtls ignorée (montant ou type manquant): Date={date_str_final}")
                                continue # Ignorer si montant ou type manquant

                            try:
                                transaction_date = datetime.strptime(date_str_final, '%Y-%m-%d').date()
                            except ValueError:
                                logger.error(f"Erreur format date XML TxDtls: '{date_str_final}'. Attendu 'YYYY-MM-DD'.")
                                raise ValueError(f"Format de date invalide pour '{date_str_final}'. Attendu 'YYYY-MM-DD'.")

                            amount = Decimal(amount_str)
                            transaction_type = 'IN' if CdtDbtInd == 'CRDT' else 'OUT'

                            transactions_data.append({
                                'date': transaction_date,
                                'description': description,
                                'amount': amount,
                                'account': account,
                                'transaction_type': transaction_type,
                                'category': None
                            })
                            logger.debug(f"TxDtls ajoutée: {description} {amount} {transaction_type}")

                    else: # C'est une entrée Ntry simple (non groupée)
                        logger.debug(f"Opération simple détectée pour Ntry {entry_num + 1}. Traitement direct.")
                        date_str_final = entry_bookg_date_str
                        amount_node = entry.xpath('./ns:Amt/text()', namespaces=ns) 
                        if not amount_node:
                            amount_node = entry.xpath('./ns:Amt/ns:InstdAmt/text()', namespaces=ns)
                        amount_str = amount_node[0] if amount_node else None

                        CdtDbtInd_node = entry.xpath('./ns:CdtDbtInd/text()', namespaces=ns)
                        CdtDbtInd = CdtDbtInd_node[0] if CdtDbtInd_node else None
                        
                        # --- LOGIQUE DE DESCRIPTION PRÉCISE POUR Ntry simple ---
                        main_description_parts = []
                        secondary_details = [] # Initialisation pour chaque entrée simple

                        # 1. Informations additionnelles de l'entrée (AddtlNtryInf) - Souvent le libellé principal ici
                        addtl_ntry_info_node = entry.xpath('./ns:AddtlNtryInf/text()', namespaces=ns)
                        if addtl_ntry_info_node:
                            main_description_parts.append(addtl_ntry_info_node[0].strip())

                        # 2. Informations de remise non structurées (Ustrd) - Peut compléter AddtlNtryInf
                        remittance_ustrd_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RmtInf/ns:Ustrd/text()', namespaces=ns)
                        if remittance_ustrd_node and remittance_ustrd_node[0].strip() not in main_description_parts:
                            main_description_parts.append(remittance_ustrd_node[0].strip())

                        # 3. Nom du Débiteur/Créditeur (Partie liée) - Toujours pertinent
                        related_party_name = None
                        dbtr_name_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:Dbtr/ns:Pty/ns:Nm/text()', namespaces=ns)
                        cdtr_name_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:Cdtr/ns:Pty/ns:Nm/text()', namespaces=ns)
                        
                        if CdtDbtInd == 'DBIT' and cdtr_name_node:
                            related_party_name = cdtr_name_node[0].strip()
                        elif CdtDbtInd == 'CRDT' and dbtr_name_node:
                            related_party_name = dbtr_name_node[0].strip()
                        
                        if related_party_name and related_party_name not in main_description_parts:
                            main_description_parts.insert(0, related_party_name) # Ajouter au début si pertinent

                        # 4. Référence de paiement structurée (Ref) ou AddtlRmtInf
                        remittance_strd_ref_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref/text()', namespaces=ns)
                        if remittance_strd_ref_node:
                            secondary_details.append(f"Ref: {remittance_strd_ref_node[0].strip()}")
                        
                        remittance_addtl_strd_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RmtInf/ns:Strd/ns:AddtlRmtInf/text()', namespaces=ns)
                        if remittance_addtl_strd_node:
                            secondary_details.append(remittance_addtl_strd_node[0].strip())

                        # 5. Bank Transaction Code (Prtry/Nm ou Cd)
                        bk_tx_cd_node_nm = entry.xpath('.//ns:BkTxCd/ns:Prtry/ns:Nm/text()', namespaces=ns)
                        if not bk_tx_cd_node_nm:
                            bk_tx_cd_node_nm = entry.xpath('.//ns:BkTxCd/ns:Prtry/ns:Cd/text()', namespaces=ns)
                        if bk_tx_cd_node_nm and bk_tx_cd_node_nm[0].strip() not in main_description_parts and bk_tx_cd_node_nm[0].strip() not in secondary_details:
                            secondary_details.append(f"Code Tx: {bk_tx_cd_node_nm[0].strip()}")

                        # 6. IBAN de la contrepartie
                        counterparty_iban = None
                        dbtr_iban_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:DbtrAcct/ns:Id/ns:IBAN/text()', namespaces=ns)
                        cdtr_iban_node = entry.xpath('.//ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:IBAN/text()', namespaces=ns)
                        
                        if CdtDbtInd == 'DBIT' and cdtr_iban_node:
                            counterparty_iban = cdtr_iban_node[0].strip()
                        elif CdtDbtInd == 'CRDT' and dbtr_iban_node:
                            counterparty_iban = dbtr_iban_node[0].strip()
                        
                        if counterparty_iban:
                            secondary_details.append(f"IBAN: {counterparty_iban}")

                        description = " - ".join(filter(None, main_description_parts))
                        if secondary_details:
                            description += f" ({' ; '.join(filter(None, secondary_details))})"
                        
                        if not description.strip():
                            description = "Description non trouvée (Ntry)"
                        # --- FIN LOGIQUE DE DESCRIPTION PRÉCISE ---

                        # MODIFIÉ: Vérification de la validité de date_str_final
                        if not date_str_final:
                            logger.warning(f"Entrée XML simple ignorée (date manquante): Montant={amount_str}, CdtDbtInd={CdtDbtInd}")
                            continue # Ignorer cette transaction si la date est manquante

                        if not all([amount_str, CdtDbtInd]):
                            logger.warning(f"Entrée XML simple ignorée (montant ou type manquant): Date={date_str_final}")
                            continue # Ignorer si montant ou type manquant

                        try:
                            transaction_date = datetime.strptime(date_str_final, '%Y-%m-%d').date()
                        except ValueError:
                            logger.error(f"Erreur format date XML simple: '{date_str_final}'. Attendu 'YYYY-MM-DD'.")
                            raise ValueError(f"Format de date invalide pour '{date_str_final}'. Attendu 'YYYY-MM-DD'.")

                        amount = Decimal(amount_str)
                        transaction_type = 'IN' if CdtDbtInd == 'CRDT' else 'OUT'

                        transactions_data.append({
                            'date': transaction_date,
                            'description': description,
                            'amount': amount,
                            'account': account,
                            'transaction_type': transaction_type,
                            'category': None
                        })
                        logger.debug(f"Transaction simple ajoutée: {description} {amount} {transaction_type}")

            return transactions_data
        except etree.XMLSyntaxError as e:
            logger.error(f"Erreur de syntaxe XML: {e}. Le fichier est peut-être malformé.")
            raise ValueError(f"Erreur de syntaxe XML: {e}. Le fichier est peut-être malformé.")
        except Exception as e:
            logger.critical(f"Erreur lors du parsing du fichier XML ISO: {e}. Assurez-vous du format et des chemins XPath.", exc_info=True)
            raise ValueError(f"Erreur lors du parsing du fichier XML ISO: {e}. Assurez-vous du format et des chemins XPath.")
