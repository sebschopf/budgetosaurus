# webapp/importers/__init__.py
# Ce fichier rend le dossier 'importers' un paquet Python
# et expose les classes d'importateurs pour une importation facile.

from .base import BaseTransactionImporter
from .csv_generic import CsvGenericImporter
from .csv_raiffeisen import CsvRaiffeisenImporter
from .xml_iso import XmlIsoImporter
from .swift_mt940 import SwiftMt940Importer

# Vous pouvez définir __all__ pour contrôler ce qui est importé avec 'from importers import *'
__all__ = [
    'BaseTransactionImporter',
    'CsvGenericImporter',
    'CsvRaiffeisenImporter',
    'XmlIsoImporter',
    'SwiftMt940Importer',
]
