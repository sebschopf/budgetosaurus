# webapp/importers/__init__.py
# Ce fichier rend le dossier 'importers' un paquet Python
# et expose les classes d'importateurs pour une importation facile.

from .base import BaseTransactionImporter
from .csv_generic import CsvTransactionImporter
from .csv_raiffeisen import RaiffeisenCsvTransactionImporter
from .xml_iso import XmlIsoTransactionImporter
from .swift_mt940 import SwiftMt940TransactionImporter

# Vous pouvez définir __all__ pour contrôler ce qui est importé avec 'from importers import *'
__all__ = [
    'BaseTransactionImporter',
    'CsvTransactionImporter',
    'RaiffeisenCsvTransactionImporter',
    'XmlIsoTransactionImporter',
    'SwiftMt940TransactionImporter',
]
