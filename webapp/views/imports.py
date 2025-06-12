import os
import csv
import io
import tempfile
import xml.etree.ElementTree as ET
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from webapp.models import Transaction, Account
from webapp.forms.transaction_import_form import TransactionImportForm
from webapp.importers.csv_raiffeisen import CsvRaiffeisenImporter
from webapp.importers.csv_generic import CsvGenericImporter
from webapp.importers.xml_iso import XmlIsoImporter
from webapp.importers.swift_mt940 import SwiftMt940Importer
from webapp.services.transaction_import_service import TransactionImportService

@login_required
def import_transactions_view(request):
    """
    Vue pour importer des transactions depuis différents formats de fichiers bancaires.
    """
    if request.method == 'POST':
        form = TransactionImportForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            uploaded_file = request.FILES.get('csv_file')  # Le nom du champ est toujours 'csv_file' même pour XML
            account = form.cleaned_data['account']
            importer_type = form.cleaned_data['importer_type']
            
            if not uploaded_file:
                messages.error(request, "Veuillez sélectionner un fichier.")
                return render(request, 'webapp/import_transactions.html', {'form': form})
            
            # Vérifier l'extension du fichier selon le type d'importateur
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            if importer_type == 'generic_csv' and file_extension != '.csv':
                messages.error(request, "Pour l'importateur CSV générique, le fichier doit être au format CSV.")
                return render(request, 'webapp/import_transactions.html', {'form': form})
            
            if importer_type == 'raiffeisen_csv' and file_extension != '.csv':
                messages.error(request, "Pour l'importateur Raiffeisen CSV, le fichier doit être au format CSV.")
                return render(request, 'webapp/import_transactions.html', {'form': form})
            
            if importer_type == 'xml_iso' and file_extension != '.xml':
                messages.error(request, "Pour l'importateur XML ISO, le fichier doit être au format XML.")
                return render(request, 'webapp/import_transactions.html', {'form': form})
            
            if importer_type == 'swift_mt940' and file_extension not in ['.mt940', '.sta', '.txt']:
                messages.error(request, "Pour l'importateur SWIFT MT940, le fichier doit être au format MT940, STA ou TXT.")
                return render(request, 'webapp/import_transactions.html', {'form': form})
            
            # Sauvegarder temporairement le fichier
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            for chunk in uploaded_file.chunks():
                temp_file.write(chunk)
            temp_file.close()
            
            try:
                # Sélectionner l'importateur approprié
                if importer_type == 'generic_csv':
                    config = {
                        'date_column_index': 0,  # À adapter selon votre formulaire
                        'description_column_index': 1,
                        'amount_column_index': 2,
                        'date_format': '%Y-%m-%d',  # À adapter selon votre formulaire
                        'header_rows': 1,  # À adapter selon votre formulaire
                    }
                    importer = CsvGenericImporter(config)
                elif importer_type == 'raiffeisen_csv':
                    importer = CsvRaiffeisenImporter()
                elif importer_type == 'xml_iso':
                    importer = XmlIsoImporter()
                    
                    # Vérification supplémentaire pour les fichiers XML
                    try:
                        tree = ET.parse(temp_file.name)
                        root = tree.getroot()
                        # Vérifier si le fichier XML est au format camt.053
                        if 'camt.053' not in root.tag and not any('camt.053' in child.tag for child in root):
                            messages.error(request, "Le fichier XML ne semble pas être au format camt.053.")
                            os.unlink(temp_file.name)
                            return render(request, 'webapp/import_transactions.html', {'form': form})
                    except ET.ParseError as e:
                        messages.error(request, f"Erreur de parsing XML: {str(e)}")
                        os.unlink(temp_file.name)
                        return render(request, 'webapp/import_transactions.html', {'form': form})
                    
                elif importer_type == 'swift_mt940':
                    importer = SwiftMt940Importer()
                else:
                    messages.error(request, "Type d'importateur non reconnu.")
                    os.unlink(temp_file.name)  # Supprimer le fichier temporaire
                    return render(request, 'webapp/import_transactions.html', {'form': form})
                
                # Créer le service d'importation
                import_service = TransactionImportService(importer)
                
                # Importer les transactions
                try:
                    imported_count = import_service.process_import(temp_file.name, account, request.user)
                    
                    if imported_count > 0:
                        messages.success(request, f"{imported_count} transaction(s) importée(s) avec succès.")
                    else:
                        messages.info(request, "Aucune transaction n'a été importée.")
                        
                except ValueError as e:
                    messages.error(request, f"Erreur de validation: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Erreur lors de l'importation: {str(e)}")
                
            except Exception as e:
                messages.error(request, f"Erreur lors de l'importation: {str(e)}")
            finally:
                # Nettoyer le fichier temporaire
                if os.path.exists(temp_file.name):
                    os.unlink(temp_file.name)
            
            return redirect('dashboard_view')
        else:
            # Le formulaire n'est pas valide, afficher les erreurs
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erreur dans le champ {field}: {error}")
    else:
        form = TransactionImportForm(user=request.user)
    
    return render(request, 'webapp/import_transactions.html', {'form': form})
