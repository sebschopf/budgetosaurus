# webapp/importers/base.py
from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime

class BaseTransactionImporter(ABC):
    """
    Classe abstraite définissant l'interface pour tous les importateurs de transactions.
    Chaque importateur concret (CSV, Excel, etc.) doit implémenter cette interface.
    """
    @abstractmethod
    def import_transactions(self, file_content: str, account, column_mapping: dict = None) -> list[dict]:
        """
        Importe les transactions depuis le contenu du fichier pour le compte donné.
        
        Args:
            file_content (str): Le contenu du fichier (CSV, etc.) sous forme de chaîne.
            account (Account): L'instance du modèle Account vers lequel les transactions sont importées.
            column_mapping (dict, optional): Un dictionnaire mappant les noms de champs internes
                                             aux noms de colonnes réels dans le fichier.
                                             Peut être ignoré par les importateurs qui ont un format fixe.
                                             
        Returns:
            list[dict]: Une liste de dictionnaires, chaque dictionnaire représentant
                        les données d'une transaction prêtes à être créées.
                        Ex: [{'date': date_obj, 'description': '...', 'amount': Decimal, ...}]
        """
        pass
