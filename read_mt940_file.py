# read_mt940_file.py
import mt940
from decimal import Decimal
from datetime import datetime

# Remplacez 'chemin/vers/votre/fichier.mt940' par le chemin réel de votre fichier
# Exemple: 'C:\\Users\\sebas\\Documents\\budgetosaurus\\mon_releve.mt940'
FILE_PATH = 'C:\Users\sebas\Downloads/Konto_CH1980808005986006920_20250604112350.mt940' # <--- MODIFIEZ CE CHEMIN

def read_mt940(file_path):
    """
    Lit et parse un fichier MT940 et affiche ses transactions.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Erreur de décodage UTF-8 pour {file_path}. Essai avec latin-1...")
        with open(file_path, 'r', encoding='latin-1') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Erreur: Le fichier '{file_path}' n'a pas été trouvé.")
        return
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier '{file_path}': {e}")
        return

    try:
        statements = mt940.parse(content)
        print(f"\n--- Parsing du fichier: {file_path} ---")
        print(f"Nombre total de relevés trouvés: {len(statements)}\n")

        for stmt_num, statement in enumerate(statements):
            print(f"--- Relevé {stmt_num + 1} ---")
            print(f"  Données du relevé: {statement.data}")
            print(f"  Nombre de transactions dans ce relevé: {len(statement.transactions)}")
            print("-" * 30)

            if not statement.transactions:
                print("  Aucune transaction trouvée dans ce relevé.")
                continue

            for tx_num, transaction in enumerate(statement.transactions):
                print(f"  Transaction {tx_num + 1}:")
                # Accéder aux attributs de l'objet transaction et son dictionnaire .data
                date_obj = transaction.data.get('date')
                amount_obj = transaction.data.get('amount')
                status_indicator = transaction.data.get('status') # 'C' ou 'D'

                amount_value = Decimal(str(amount_obj.amount)) if amount_obj and hasattr(amount_obj, 'amount') else 'N/A'
                is_credit = amount_obj.is_credit if amount_obj and hasattr(amount_obj, 'is_credit') else 'N/A' # Vérifier si l'attribut existe
                
                # Pour la description, explorez les champs courants
                description = transaction.data.get('transaction_details', '').strip()
                if not description:
                    description = transaction.data.get('description', '').strip()
                if not description:
                    description = transaction.data.get('additional_transaction_info', '').strip()
                if not description:
                    description = transaction.data.get('remittance_information', '').strip()
                if not description:
                    description = transaction.data.get('non_swift', '').strip() # Parfois, des infos non-SWIFT sont là
                if not description:
                    description = transaction.data.get('extra_details', '').strip() # Parfois, des infos supplémentaires
                
                print(f"    Date: {date_obj}")
                print(f"    Montant (objet): {amount_obj}")
                print(f"    Valeur Montant: {amount_value}")
                print(f"    Est Crédit (from amount_obj): {is_credit}")
                print(f"    Statut (from data): {status_indicator}")
                print(f"    Description: {description}")
                print(f"    Données brutes (transaction.data): {transaction.data}")
                print("-" * 40)

    except mt940.errors.MT940ParseException as e:
        print(f"\nErreur de parsing MT940: {e}")
        print("Veuillez vérifier le format de votre fichier. Il pourrait ne pas être un MT940 standard.")
    except Exception as e:
        print(f"\nUne erreur inattendue est survenue lors du parsing: {e}")
        print("Cela pourrait indiquer un problème avec la bibliothèque ou un fichier très malformé.")

if __name__ == "__main__":
    # Remplacez par le chemin de votre fichier MT940
    read_mt940(FILE_PATH)
