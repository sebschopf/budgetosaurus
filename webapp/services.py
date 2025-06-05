# webapp/services.py
from django.db import transaction as db_transaction
from django.db.models import Sum
from webapp.models import Transaction, Account, Category, Fund, CategorizationRule, Tag # Importez CategorizationRule et Tag
from webapp.importers import BaseTransactionImporter
from datetime import date
import logging
from django.utils import timezone 
from decimal import Decimal, InvalidOperation # Assurez-vous d'importer Decimal et InvalidOperation

# Import pour le fuzzy matching
from fuzzywuzzy import fuzz
from fuzzywuzzy import process # Utile pour trouver la meilleure correspondance parmi plusieurs

logger = logging.getLogger(__name__)

class TransactionService:
    """
    Service de gestion des transactions. Encapsule la logique métier liée aux transactions
    pour respecter le Principe de Responsabilité Unique (SRP).
    """
    def create_transaction(self, data: dict) -> Transaction:
        """
        Crée et sauvegarde une nouvelle transaction.
        Met à jour le solde du fonds budgétaire associé si la transaction est une dépense
        ou un revenu (hors compte de type 'COMMON' ou 'SAVINGS' pour les revenus) ET si la catégorie
        est marquée comme gérant un fonds (`is_fund_managed`).
        Apprend de la transaction pour les règles de catégorisation.
        
        Args:
            data (dict): Dictionnaire des données de la transaction (date, description, amount, etc.).
                         Le champ 'category' doit être l'objet Category final (sous-catégorie ou catégorie principale).
                         Le champ 'tags' doit être une liste d'objets Tag.
        
        Returns:
            Transaction: L'instance de la transaction créée.
        """
        with db_transaction.atomic():
            # Extraire les tags de 'data' car ils sont un ManyToManyField et doivent être définis après la création de l'instance
            tags_data = data.pop('tags', [])
            transaction = Transaction.objects.create(**data)
            transaction.tags.set(tags_data) # Associe les tags à la transaction

            # Logique de mise à jour des fonds :
            # UNIQUEMENT si la catégorie est marquée comme "gérant un fonds" (`is_fund_managed`)
            # et si le type de transaction n'est pas 'TRF'.
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount))
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (dépense): soustraction de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (dépense) pour la transaction {transaction.id}: {e}", exc_info=True)
                
                elif transaction.transaction_type == 'IN':
                    # Seuls les revenus sur les comptes INDIVIDUALS affectent directement les fonds catégorisés.
                    # Les revenus sur les comptes COMMUNS ou EPARGNE sont gérés différemment (allocations ou hors budget).
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount))
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (revenu individuel): ajout de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category).current_balance}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (revenu individuel) pour la transaction {transaction.id}: {e}", exc_info=True)
                    else:
                        logger.info(f"Revenu sur compte de type '{transaction.account.account_type}' (transaction {transaction.id}) ne met pas à jour un fonds directement. Attente de ventilation ou hors budget.")
            elif transaction.category and not transaction.category.is_fund_managed:
                logger.info(f"Transaction {transaction.id} (cat: {transaction.category.name}) n'affecte pas de fonds car 'is_fund_managed' est False.")
            else:
                logger.info(f"Transaction {transaction.id} (type: {transaction.transaction_type}) n'affecte pas de fonds (pas de catégorie ou est un TRF).")
            
            # Apprendre de cette transaction pour la catégorisation automatique
            self._update_categorization_rule(transaction)

            return transaction

    def update_transaction(self, transaction: Transaction, data: dict) -> Transaction:
        """
        Met à jour une transaction existante.
        Gère l'ajustement des soldes des fonds budgétaires si la catégorie, le montant ou le type de transaction change,
        ET si la catégorie est marquée comme gérant un fonds (`is_fund_managed`).
        Apprend de la transaction mise à jour pour les règles de catégorisation.

        Args:
            transaction (Transaction): L'instance de la transaction à mettre à jour.
            data (dict): Dictionnaire des données de la transaction à appliquer.

        Returns:
            Transaction: L'instance de la transaction mise à jour.
        """
        with db_transaction.atomic():
            # Sauvegarder les valeurs originales avant la mise à jour
            original_amount_normalized = transaction.amount # C'est déjà le montant normalisé (négatif pour OUT)
            original_category = transaction.category
            original_type = transaction.transaction_type
            original_account = transaction.account # Garder une trace du compte original

            # Appliquer les nouvelles données à l'instance de la transaction
            tags_data = data.pop('tags', None) # Extraire les tags avant de mettre à jour les autres champs
            for field, value in data.items():
                setattr(transaction, field, value)
            
            # Sauvegarder la transaction pour que le signal pre_save normalise le nouveau montant
            transaction.save() 
            if tags_data is not None: # Mettre à jour les tags si ils étaient dans les données
                transaction.tags.set(tags_data)

            # --- Logique d'ajustement des fonds lors d'une mise à jour ---
            # Les fonds ne sont affectés que par les transactions de type 'IN' et 'OUT'
            # et selon le type de compte pour les revenus, ET si la catégorie est "fund_managed".

            # 1. Annuler l'impact de l'ancienne transaction sur l'ancien fonds (si elle était 'IN' ou 'OUT' et avait une catégorie fund_managed)
            if original_category and original_type != 'TRF' and original_category.is_fund_managed:
                if original_type == 'OUT':
                    try:
                        # Annuler la dépense précédente en ajoutant le montant (positif) à l'ancien fonds
                        Fund.objects.add_funds_to_category(original_category, abs(original_amount_normalized))
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancienne dépense): ajout de {abs(original_amount_normalized)}. Nouveau solde: {Fund.objects.get(category=original_category).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancienne dépense) pour la transaction {transaction.id}: {e}", exc_info=True)
                elif original_type == 'IN' and original_account.account_type == 'INDIVIDUAL':
                    try:
                        # Annuler le revenu précédent en soustrayant le montant (positif) de l'ancien fonds
                        Fund.objects.subtract_funds_from_category(original_category, abs(original_amount_normalized))
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancien revenu individuel): soustraction de {abs(original_amount_normalized)}. Nouveau solde: {Fund.objects.get(category=original_category).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancien revenu individuel) pour la transaction {transaction.id}: {e}", exc_info=True)
                else:
                    logger.info(f"Ancienne transaction {transaction.id} (type: {original_type}, compte: {original_account.get_account_type_display()}) n'a pas affecté les fonds catégorisés (ou catégorie non fund_managed), pas d'annulation nécessaire.")
            elif original_category and not original_category.is_fund_managed:
                 logger.info(f"Ancienne transaction {transaction.id} (cat: {original_category.name}) n'affectait pas de fonds car 'is_fund_managed' était False.")
            else:
                logger.info(f"Ancienne transaction {transaction.id} (pas de catégorie ou TRF) n'a pas affecté les fonds.")


            # 2. Appliquer l'impact de la nouvelle transaction sur le nouveau fonds (si elle est 'IN' ou 'OUT' et a une catégorie fund_managed)
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        # Appliquer la nouvelle dépense en soustrayant le montant (positif) du nouveau fonds
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount)) # transaction.amount est déjà normalisé
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouvelle dépense): soustraction de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (nouvelle dépense) pour la transaction {transaction.id}: {e}", exc_info=True)
                elif transaction.transaction_type == 'IN':
                    # Seuls les revenus sur les comptes INDIVIDUALS affectent directement les fonds catégorisés.
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            # Appliquer le nouveau revenu en ajoutant le montant (positif) au nouveau fonds
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount)) # transaction.amount est déjà normalisé
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouveau revenu individuel): ajout de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category).current_balance}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (nouvel revenu individuel) pour la transaction {transaction.id}: {e}", exc_info=True)
                    else:
                        logger.info(f"Nouveau revenu sur compte de type '{transaction.account.account_type}' (transaction {transaction.id}) ne met pas à jour un fonds directement. Attente de ventilation ou hors budget.")
            elif transaction.category and not transaction.category.is_fund_managed:
                logger.info(f"Nouvelle transaction {transaction.id} (cat: {transaction.category.name}) n'affecte pas de fonds car 'is_fund_managed' est False.")
            else:
                logger.info(f"Nouvelle transaction {transaction.id} (pas de catégorie ou TRF) n'affecte pas les fonds catégorisés.")

            # Apprendre de cette transaction mise à jour pour la catégorisation automatique
            self._update_categorization_rule(transaction)

            return transaction

    def _update_categorization_rule(self, transaction: Transaction):
        """
        Crée ou met à jour une règle de catégorisation basée sur une transaction.
        Cette méthode est appelée après la création ou la mise à jour d'une transaction
        pour enregistrer les préférences de catégorisation de l'utilisateur.
        """
        # Une règle n'est pertinente que si la transaction a une description et une catégorie.
        if not transaction.description or not transaction.category:
            logger.debug(f"Pas de mise à jour de règle de catégorisation pour transaction {transaction.id}: description ou catégorie manquante.")
            return 

        try:
            # Tente de récupérer une règle existante basée sur le modèle de description.
            # Si aucune n'existe, en crée une nouvelle avec les valeurs par défaut.
            rule, created = CategorizationRule.objects.get_or_create(
                description_pattern=transaction.description,
                defaults={
                    'suggested_category': transaction.category,
                    'hit_count': 1, # Initialise à 1 pour une nouvelle règle
                    'last_applied_at': timezone.now()
                }
            )
            if not created:
                # Si la règle existe déjà, mettez à jour ses attributs.
                # La catégorie suggérée est mise à jour avec la catégorie actuelle de la transaction.
                if rule.suggested_category != transaction.category:
                    logger.info(f"Mise à jour de la catégorie suggérée pour la règle '{rule.description_pattern}': de '{rule.suggested_category}' à '{transaction.category}'.")
                    rule.suggested_category = transaction.category
                
                # Les tags suggérés sont mis à jour pour correspondre aux tags actuels de la transaction.
                # Utilise set() pour gérer l'ajout/suppression efficace des relations ManyToMany.
                current_tags_on_rule = set(rule.suggested_tags.all())
                new_tags_for_rule = set(transaction.tags.all())
                
                if current_tags_on_rule != new_tags_for_rule:
                    logger.info(f"Mise à jour des tags suggérés pour la règle '{rule.description_pattern}'.")
                    rule.suggested_tags.set(new_tags_for_rule) 

                # Incrémente le compteur d'occurrences et met à jour la date de dernière application.
                rule.hit_count += 1
                rule.last_applied_at = timezone.now()
                rule.save() # Sauvegarde les modifications apportées à la règle
            
            logger.info(f"Règle de catégorisation {'créée' if created else 'mise à jour'} pour '{transaction.description}'")

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la règle de catégorisation pour '{transaction.description}': {e}", exc_info=True)

    def get_account_balances(self) -> dict:
        """
        Récupère les soldes actuels de tous les comptes.
        Les montants des transactions sont déjà normalisés (dépenses négatives, revenus positifs)
        grâce au signal pre_save.
        """
        accounts = Account.objects.all().order_by('name')
        account_balances = {}
        for account in accounts:
            total_balance_change = account.transactions.aggregate(Sum('amount'))['amount__sum'] or 0
            balance = account.initial_balance + total_balance_change
            account_balances[account.name] = {
                'balance': balance,
                'currency': account.currency
            }
        return account_balances

    def get_latest_transactions(self, limit: int = 10) -> list[Transaction]:
        """
        Récupère les N dernières transactions.
        Optimise les requêtes en utilisant select_related pour les clés étrangères
        et prefetch_related pour les relations ManyToMany (tags).
        """
        return Transaction.objects.all().select_related('category', 'account').prefetch_related('tags').order_by('-date', '-created_at')[:limit]

    def split_transaction(self, original_transaction: Transaction, split_lines_data: list[dict]):
        """
        Divise une transaction originale en plusieurs nouvelles transactions.
        Supprime la transaction originale après la création réussie des nouvelles.
        Assure l'atomicité de l'opération.

        Args:
            original_transaction (Transaction): La transaction à diviser.
            split_lines_data (list[dict]): Une liste de dictionnaires, où chaque dict
                                           contient les données (description, amount, category, etc.)
                                           pour une nouvelle transaction de division.
        Raises:
            ValueError: Si la somme des montants divisés ne correspond pas au montant original.
            Exception: Pour d'autres erreurs lors de la création ou suppression.
        """
        with db_transaction.atomic():
            total_split_amount = Decimal('0.00')
            for line_data in split_lines_data:
                # S'assurer que les signes des montants sont corrects pour les nouvelles transactions
                # Si la transaction originale est une dépense, les divisions doivent être des dépenses
                # Si la transaction originale est un revenu, les divisions doivent être des revenus
                # Les montants doivent être positifs pour la création (le signal pre_save s'occupe du signe final)
                amount = line_data['amount']
                if original_transaction.transaction_type == 'OUT':
                    if amount > 0:
                        amount = -amount
                elif original_transaction.transaction_type == 'IN':
                    if amount < 0:
                        amount = abs(amount)
                
                total_split_amount += abs(amount) # Utiliser l'absolu pour la somme de comparaison

            # Validation du montant total (avec tolérance)
            if abs(total_split_amount - abs(original_transaction.amount)) > Decimal('0.01'):
                raise ValueError(
                    f"La somme des montants divisés ({total_split_amount:.2f} CHF) "
                    f"ne correspond pas au montant original ({abs(original_transaction.amount):.2f} CHF)."
                )

            # Créer les nouvelles transactions
            for line_data in split_lines_data:
                # Construire les données pour la nouvelle transaction
                new_tx_data = {
                    'date': original_transaction.date,
                    'description': line_data['description'],
                    'amount': line_data['amount'], # Le signal pre_save ajustera le signe
                    'category': line_data['category'], # C'est déjà l'objet Category final
                    'account': original_transaction.account,
                    'transaction_type': original_transaction.transaction_type,
                    'tags': line_data.get('tags', []), # Assurez-vous d'avoir les tags si pertinents
                }
                self.create_transaction(new_tx_data) # Appelle la méthode existante pour créer et mettre à jour les fonds

            # Supprimer la transaction originale après la création réussie des nouvelles transactions
            original_transaction.delete()
            logger.info(f"Transaction originale {original_transaction.id} divisée et supprimée.")


    def suggest_categorization(self, description: str):
        """
        Suggère une catégorie et des tags basés sur la description de la transaction,
        en utilisant le fuzzy matching si aucune correspondance exacte n'est trouvée.
        """
        if not description:
            return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        # 1. Cherche une règle exacte
        exact_rule = CategorizationRule.objects.filter(description_pattern=description).first()

        if exact_rule and exact_rule.suggested_category:
            rule_to_use = exact_rule
            logger.debug(f"Suggestion exacte trouvée pour '{description}'.")
        else:
            # 2. Si pas de correspondance exacte, cherche la meilleure correspondance floue
            all_rules = CategorizationRule.objects.all()
            if not all_rules.exists():
                return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

            # Crée une liste de toutes les descriptions de règles pour le fuzzy matching
            rule_descriptions = {rule.description_pattern: rule for rule in all_rules}
            
            # Utilise process.extractOne pour trouver la meilleure correspondance floue
            # Le score est entre 0 et 100. On fixe un seuil de pertinence.
            # Vous pouvez ajuster ce seuil (ex: 80, 85, 90) selon la précision désirée.
            FUZZY_MATCH_THRESHOLD = 85 
            
            best_match = process.extractOne(description, rule_descriptions.keys(), scorer=fuzz.ratio)
            
            rule_to_use = None
            if best_match and best_match[1] >= FUZZY_MATCH_THRESHOLD:
                matched_description_pattern = best_match[0]
                rule_to_use = rule_descriptions[matched_description_pattern]
                logger.debug(f"Suggestion floue trouvée pour '{description}' (match: '{matched_description_pattern}', score: {best_match[1]}).")
            else:
                logger.debug(f"Aucune suggestion (exacte ou floue) trouvée pour '{description}'.")
                return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        # Si une règle (exacte ou floue) a été trouvée et a une catégorie suggérée
        if rule_to_use and rule_to_use.suggested_category:
            suggested_category = rule_to_use.suggested_category
            suggested_tags = list(rule_to_use.suggested_tags.all()) # Convertir en liste d'objets Tag

            # Mettre à jour le hit_count et last_applied_at de la règle utilisée
            try:
                rule_to_use.hit_count += 1
                rule_to_use.last_applied_at = timezone.now()
                rule_to_use.save()
                logger.debug(f"Règle de catégorisation '{rule_to_use.description_pattern}' hit_count incrémenté à {rule_to_use.hit_count}.")
            except Exception as e:
                logger.error(f"Erreur lors de l'incrémentation du hit_count pour la règle '{rule_to_use.description_pattern}': {e}", exc_info=True)

            parent_category_id = None
            parent_category_name = None
            subcategory_id = None
            subcategory_name = None

            # Détermine si la catégorie suggérée est une sous-catégorie ou une catégorie principale
            if suggested_category.parent:
                parent_category_id = suggested_category.parent.id
                parent_category_name = suggested_category.parent.name
                subcategory_id = suggested_category.id
                subcategory_name = suggested_category.name
            else:
                parent_category_id = suggested_category.id
                parent_category_name = suggested_category.name

            return {
                'category_id': parent_category_id,
                'category_name': parent_category_name,
                'subcategory_id': subcategory_id,
                'subcategory_name': subcategory_name,
                'tag_ids': [tag.id for tag in suggested_tags],
                'tag_names': [tag.name for tag in suggested_tags]
            }
        
        # Retourne des valeurs vides si aucune règle n'est trouvée ou si la catégorie suggérée est nulle
        return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}


class TransactionImportService:
    """
    Service dédié à l'importation de transactions depuis des fichiers.
    Respecte le Principe d'Inversion de Dépendances (DIP) en dépendant d'une abstraction
    (BaseTransactionImporter) plutôt que d'une implémentation concrète.
    """
    def __init__(self, importer: BaseTransactionImporter):
        """
        Initialise le service d'importation avec un importateur spécifique.
        
        Args:
            importer (BaseTransactionImporter): L'instance de l'importateur à utiliser
                                                (ex: CsvTransactionImporter).
        """
        self.importer = importer

    def process_import(self, file_content: str, account: Account, column_mapping: dict = None) -> int:
        """
        Traite le fichier importé, extrait les transactions et les sauvegarde dans la base de données.
        Gère les transactions atomiques et la détection des doublons.
        Utilise TransactionService pour la création et la logique d'apprentissage.
        
        Args:
            file_content (str): Le contenu du fichier à importer.
            account (Account): Le compte de destination pour les transactions.
            column_mapping (dict, optional): Le mappage des colonnes fourni par l'utilisateur.
                                             Peut être None si l'importateur n'en a pas besoin.
            
        Returns:
            int: Le nombre de transactions importées avec succès.
        
        Raises:
            ValueError: Si le format du fichier ou le mappage est invalide.
            Exception: Pour toute autre erreur lors de l'importation/sauvegarde.
        """
        imported_count = 0
        errors = []
        transaction_service = TransactionService() # Utilise le TransactionService pour la création et l'apprentissage

        with db_transaction.atomic():
            try:
                transactions_data = self.importer.import_transactions(file_content, account, column_mapping)

                for data in transactions_data:
                    # Pour la détection de doublons, on compare le montant tel qu'il sera stocké dans la DB.
                    # Le signal pre_save de Transaction gère la normalisation du montant (dépense négative, revenu positif).
                    # Donc, si l'importateur renvoie des montants toujours positifs, nous devons simuler le signe ici pour la comparaison.
                    amount_for_comparison = data['amount']
                    if data['transaction_type'] == 'OUT':
                        amount_for_comparison = -amount_for_comparison 

                    existing_transaction = Transaction.objects.filter(
                        date=data['date'],
                        description=data['description'],
                        amount=amount_for_comparison, # Comparaison avec le montant normalisé
                        account=data['account']
                    ).first()

                    if existing_transaction:
                        logger.info(f"Transaction doublon détectée et ignorée lors de l'importation: {data['description']} le {data['date']}")
                        continue

                    # Préparation des données pour le TransactionService.create_transaction
                    # Assurez-vous que 'tags' est toujours une liste, même vide
                    transaction_data_for_service = {
                        'date': data['date'],
                        'description': data['description'],
                        'amount': data['amount'], # Le signal gérera le signe
                        'account': data['account'],
                        'transaction_type': data['transaction_type'],
                        'category': data.get('category'), # Peut être None
                        'tags': data.get('tags', []), # Peut être une liste vide
                    }
                    
                    # La création via TransactionService déclenchera la logique de fonds et d'apprentissage
                    transaction_service.create_transaction(transaction_data_for_service)
                    imported_count += 1

            except ValueError as e:
                logger.error(f"Erreur de valeur lors de l'importation des transactions: {e}", exc_info=True)
                raise e
            except Exception as e:
                logger.critical(f"Erreur inattendue lors du traitement d'une transaction importée: {e}", exc_info=True)
                errors.append(f"Erreur lors de l'importation des transactions: {e}")
                raise Exception(f"Erreur lors de l'importation des transactions: {e}")

        if errors:
            raise Exception("Des erreurs sont survenues lors de l'importation: " + "; ".join(errors))
            
        return imported_count

