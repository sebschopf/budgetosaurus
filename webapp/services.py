# webapp/services.py
from django.db import transaction as db_transaction
from django.db.models import Sum
from webapp.models import Transaction, Account, Category, Fund, CategorizationRule, Tag
from webapp.importers import BaseTransactionImporter
from datetime import date
import logging
from django.utils import timezone
from decimal import Decimal, InvalidOperation

# Import pour le fuzzy matching
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

logger = logging.getLogger(__name__)

class TransactionService:
    """
    Service de gestion des transactions. Encapsule la logique métier liée aux transactions
    pour respecter le Principe de Responsabilité Unique (SRP).
    Toutes les opérations ici sont maintenant liées à un utilisateur spécifique.
    """
    def create_transaction(self, data: dict, user) -> Transaction: # Ajout de 'user'
        """
        Crée et sauvegarde une nouvelle transaction pour un utilisateur donné.
        Met à jour le solde du fonds budgétaire associé si pertinent.
        Apprend de la transaction pour les règles de catégorisation de cet utilisateur.
        """
        with db_transaction.atomic():
            # Assurez-vous que la transaction est liée à l'utilisateur
            data['user'] = user # NOUVEAU: Assigner l'utilisateur à la transaction

            # Extraire les tags de 'data' car ils sont un ManyToManyField
            tags_data = data.pop('tags', [])
            transaction = Transaction.objects.create(**data)
            transaction.tags.set(tags_data) # Associe les tags à la transaction

            # Logique de mise à jour des fonds :
            # UNIQUEMENT si la catégorie est marquée comme "gérant un fonds" (`is_fund_managed`)
            # et si le type de transaction n'est pas 'TRF'.
            # NOUVEAU: Passage de l'utilisateur aux méthodes du FundManager.
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount), user) # Passage de 'user'
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (dépense) pour utilisateur {user.username}: soustraction de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category, user=user).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)

                elif transaction.transaction_type == 'IN':
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount), user) # Passage de 'user'
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (revenu individuel) pour utilisateur {user.username}: ajout de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category, user=user).current_balance}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                    else:
                        logger.info(f"Revenu sur compte de type '{transaction.account.account_type}' (transaction {transaction.id}) pour utilisateur {user.username} ne met pas à jour un fonds directement. Attente de ventilation ou hors budget.")
            elif transaction.category and not transaction.category.is_fund_managed:
                logger.info(f"Transaction {transaction.id} (cat: {transaction.category.name}) pour utilisateur {user.username} n'affecte pas de fonds car 'is_fund_managed' est False.")
            else:
                logger.info(f"Transaction {transaction.id} (type: {transaction.transaction_type}) pour utilisateur {user.username} n'affecte pas de fonds (pas de catégorie ou est un TRF).")

            # Apprendre de cette transaction pour la catégorisation automatique
            self._update_categorization_rule(transaction, user) # Passage de 'user'

            return transaction

    def update_transaction(self, transaction: Transaction, data: dict, user) -> Transaction: # Ajout de 'user'
        """
        Met à jour une transaction existante pour un utilisateur donné.
        Gère l'ajustement des soldes des fonds budgétaires si la catégorie, le montant ou le type de transaction change,
        ET si la catégorie est marquée comme gérant un fonds (`is_fund_managed`).
        Apprend de la transaction mise à jour pour les règles de catégorisation de cet utilisateur.
        """
        # Assurez-vous que la transaction appartient à l'utilisateur (sécurité)
        if transaction.user != user:
            logger.warning(f"Tentative de mise à jour de transaction {transaction.id} par utilisateur {user.username} qui n'en est pas le propriétaire.")
            raise ValueError("Vous n'êtes pas autorisé à modifier cette transaction.")

        with db_transaction.atomic():
            # Sauvegarder les valeurs originales avant la mise à jour
            original_amount_normalized = transaction.amount
            original_category = transaction.category
            original_type = transaction.transaction_type
            original_account = transaction.account

            # Appliquer les nouvelles données à l'instance de la transaction
            tags_data = data.pop('tags', None)
            for field, value in data.items():
                setattr(transaction, field, value)

            # Assurez-vous que l'utilisateur est toujours celui qui est connecté (redondant mais sûr)
            transaction.user = user

            # Sauvegarder la transaction pour que le signal pre_save normalise le nouveau montant
            transaction.save()
            if tags_data is not None:
                transaction.tags.set(tags_data)

            # --- Logique d'ajustement des fonds lors d'une mise à jour ---
            # 1. Annuler l'impact de l'ancienne transaction sur l'ancien fonds (si elle était pertinente)
            if original_category and original_type != 'TRF' and original_category.is_fund_managed:
                if original_type == 'OUT':
                    try:
                        Fund.objects.add_funds_to_category(original_category, abs(original_amount_normalized), user) # Passage de 'user'
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancienne dépense) pour utilisateur {user.username}: ajout de {abs(original_amount_normalized)}. Nouveau solde: {Fund.objects.get(category=original_category, user=user).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancienne dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                elif original_type == 'IN' and original_account.account_type == 'INDIVIDUAL':
                    try:
                        Fund.objects.subtract_funds_from_category(original_category, abs(original_amount_normalized), user) # Passage de 'user'
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancien revenu individuel) pour utilisateur {user.username}: soustraction de {abs(original_amount_normalized)}. Nouveau solde: {Fund.objects.get(category=original_category, user=user).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancien revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                else:
                    logger.info(f"Ancienne transaction {transaction.id} (type: {original_type}, compte: {original_account.get_account_type_display()}) pour utilisateur {user.username} n'a pas affecté les fonds catégorisés (ou catégorie non fund_managed), pas d'annulation nécessaire.")
            elif original_category and not original_category.is_fund_managed:
                 logger.info(f"Ancienne transaction {transaction.id} (cat: {original_category.name}) pour utilisateur {user.username} n'affectait pas de fonds car 'is_fund_managed' était False.")
            else:
                logger.info(f"Ancienne transaction {transaction.id} (pas de catégorie ou TRF) pour utilisateur {user.username} n'a pas affecté les fonds.")


            # 2. Appliquer l'impact de la nouvelle transaction sur le nouveau fonds (si elle est pertinente)
            # Assurez-vous que transaction.category appartient au bon utilisateur
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount), user) # Passage de 'user'
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouvelle dépense) pour utilisateur {user.username}: soustraction de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category, user=user).current_balance}")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (nouvelle dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                elif transaction.transaction_type == 'IN':
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount), user) # Passage de 'user'
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouveau revenu individuel) pour utilisateur {user.username}: ajout de {abs(transaction.amount)}. Nouveau solde: {Fund.objects.get(category=transaction.category, user=user).current_balance}")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (nouvel revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                    else:
                        logger.info(f"Nouveau revenu sur compte de type '{transaction.account.account_type}' (transaction {transaction.id}) pour utilisateur {user.username} ne met pas à jour un fonds directement. Attente de ventilation ou hors budget.")
            elif transaction.category and not transaction.category.is_fund_managed:
                logger.info(f"Nouvelle transaction {transaction.id} (cat: {transaction.category.name}) pour utilisateur {user.username} n'affecte pas de fonds car 'is_fund_managed' est False.")
            else:
                logger.info(f"Nouvelle transaction {transaction.id} (pas de catégorie ou TRF) pour utilisateur {user.username} n'affecte pas les fonds catégorisés.")

            # Apprendre de cette transaction mise à jour pour la catégorisation automatique
            self._update_categorization_rule(transaction, user) # Passage de 'user'

            return transaction

    def _update_categorization_rule(self, transaction: Transaction, user): # Ajout de 'user'
        """
        Crée ou met à jour une règle de catégorisation basée sur une transaction
        pour un utilisateur spécifique.
        """
        if not transaction.description or not transaction.category:
            logger.debug(f"Pas de mise à jour de règle de catégorisation pour transaction {transaction.id}: description ou catégorie manquante.")
            return

        try:
            # Inclure l'utilisateur dans la recherche/création de la règle
            rule, created = CategorizationRule.objects.get_or_create(
                user=user, # Lier la règle à l'utilisateur
                description_pattern=transaction.description,
                defaults={
                    'suggested_category': transaction.category,
                    'hit_count': 1,
                    'last_applied_at': timezone.now()
                }
            )
            if not created:
                if rule.suggested_category != transaction.category:
                    logger.info(f"Mise à jour de la catégorie suggérée pour la règle '{rule.description_pattern}' pour utilisateur {user.username}: de '{rule.suggested_category}' à '{transaction.category}'.")
                    rule.suggested_category = transaction.category

                current_tags_on_rule = set(rule.suggested_tags.all())
                new_tags_for_rule = set(transaction.tags.all())

                if current_tags_on_rule != new_tags_for_rule:
                    logger.info(f"Mise à jour des tags suggérés pour la règle '{rule.description_pattern}' pour utilisateur {user.username}.")
                    rule.suggested_tags.set(new_tags_for_rule)

                rule.hit_count += 1
                rule.last_applied_at = timezone.now()
                rule.save()

            logger.info(f"Règle de catégorisation {'créée' if created else 'mise à jour'} pour '{transaction.description}' pour utilisateur {user.username}.")

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la règle de catégorisation pour '{transaction.description}' et utilisateur {user.username}: {e}", exc_info=True)

    def get_account_balances(self, user) -> dict: # Ajout de 'user'
        """
        Récupère les soldes actuels de tous les comptes pour un utilisateur donné.
        """
        # Filtrer les comptes par l'utilisateur
        accounts = Account.objects.filter(user=user).order_by('name')
        account_balances = {}
        for account in accounts:
            # Filtrer les transactions par l'utilisateur (car Account.transactions est toutes les transactions du compte, pas seulement celles de l'utilisateur)
            total_balance_change = account.transactions.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0
            balance = account.initial_balance + total_balance_change
            account_balances[account.name] = {
                'balance': balance,
                'currency': account.currency
            }
        return account_balances

    def get_latest_transactions(self, user, limit: int = 10) -> list[Transaction]: # Ajout de 'user'
        """
        Récupère les N dernières transactions pour un utilisateur donné.
        """
        # Filtrer les transactions par l'utilisateur
        return Transaction.objects.filter(user=user).select_related('category', 'account').prefetch_related('tags').order_by('-date', '-created_at')[:limit]

    def split_transaction(self, original_transaction: Transaction, split_lines_data: list[dict], user): # Ajout de 'user'
        """
        Divise une transaction originale en plusieurs nouvelles transactions pour un utilisateur donné.
        Supprime la transaction originale après la création réussie des nouvelles.
        """
        # Sécurité: Vérifier que la transaction originale appartient à l'utilisateur
        if original_transaction.user != user:
            logger.warning(f"Tentative de diviser une transaction {original_transaction.id} par utilisateur {user.username} qui n'en est pas le propriétaire.")
            raise ValueError("Vous n'êtes pas autorisé à diviser cette transaction.")

        with db_transaction.atomic():
            total_split_amount = Decimal('0.00')
            for line_data in split_lines_data:
                amount = line_data['amount']
                if original_transaction.transaction_type == 'OUT':
                    if amount > 0:
                        amount = -amount
                elif original_transaction.transaction_type == 'IN':
                    if amount < 0:
                        amount = abs(amount)

                total_split_amount += abs(amount)

            if abs(total_split_amount - abs(original_transaction.amount)) > Decimal('0.01'):
                raise ValueError(
                    f"La somme des montants divisés ({total_split_amount:.2f} CHF) "
                    f"ne correspond pas au montant original ({abs(original_transaction.amount):.2f} CHF)."
                )

            for line_data in split_lines_data:
                new_tx_data = {
                    'date': original_transaction.date,
                    'description': line_data['description'],
                    'amount': line_data['amount'],
                    'category': line_data['category'],
                    'account': original_transaction.account,
                    'transaction_type': original_transaction.transaction_type,
                    'tags': line_data.get('tags', []),
                }
                # Passer l'utilisateur à la méthode create_transaction
                self.create_transaction(new_tx_data, user)

            original_transaction.delete()
            logger.info(f"Transaction originale {original_transaction.id} divisée et supprimée pour utilisateur {user.username}.")


    def suggest_categorization(self, description: str, user): # Ajout de 'user'
        """
        Suggère une catégorie et des tags basés sur la description de la transaction,
        en utilisant le fuzzy matching si aucune correspondance exacte n'est trouvée,
        pour les règles propres à l'utilisateur.
        """
        if not description:
            return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        # Chercher les règles pour l'utilisateur spécifique
        exact_rule = CategorizationRule.objects.filter(user=user, description_pattern=description).first()

        if exact_rule and exact_rule.suggested_category:
            rule_to_use = exact_rule
            logger.debug(f"Suggestion exacte trouvée pour '{description}' pour utilisateur {user.username}.")
        else:
            # Filtrer toutes les règles par l'utilisateur
            all_rules = CategorizationRule.objects.filter(user=user)
            if not all_rules.exists():
                return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

            rule_descriptions = {rule.description_pattern: rule for rule in all_rules}

            FUZZY_MATCH_THRESHOLD = 85

            best_match = process.extractOne(description, rule_descriptions.keys(), scorer=fuzz.ratio)

            rule_to_use = None
            if best_match and best_match[1] >= FUZZY_MATCH_THRESHOLD:
                matched_description_pattern = best_match[0]
                rule_to_use = rule_descriptions[matched_description_pattern]
                logger.debug(f"Suggestion floue trouvée pour '{description}' pour utilisateur {user.username} (match: '{matched_description_pattern}', score: {best_match[1]}).")
            else:
                logger.debug(f"Aucune suggestion (exacte ou floue) trouvée pour '{description}' pour utilisateur {user.username}.")
                return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        if rule_to_use and rule_to_use.suggested_category:
            suggested_category = rule_to_use.suggested_category
            suggested_tags = list(rule_to_use.suggested_tags.all())

            try:
                rule_to_use.hit_count += 1
                rule_to_use.last_applied_at = timezone.now()
                rule_to_use.save()
                logger.debug(f"Règle de catégorisation '{rule_to_use.description_pattern}' pour utilisateur {user.username} hit_count incrémenté à {rule_to_use.hit_count}.")
            except Exception as e:
                logger.error(f"Erreur lors de l'incrémentation du hit_count pour la règle '{rule_to_use.description_pattern}' pour utilisateur {user.username}: {e}", exc_info=True)

            parent_category_id = None
            parent_category_name = None
            subcategory_id = None
            subcategory_name = None

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

        return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}


class TransactionImportService:
    """
    Service dédié à l'importation de transactions depuis des fichiers.
    Respecte le Principe d'Inversion de Dépendances (DIP) en dépendant d'une abstraction.
    Toutes les opérations ici sont maintenant liées à un utilisateur spécifique.
    """
    def __init__(self, importer: BaseTransactionImporter):
        self.importer = importer

    def process_import(self, file_content: str, account: Account, user, column_mapping: dict = None) -> int: # Ajout de 'user'
        """
        Traite le fichier importé, extrait les transactions et les sauvegarde dans la base de données
        pour un utilisateur donné.
        """
        imported_count = 0
        errors = []
        transaction_service = TransactionService()

        # Sécurité: S'assurer que le compte appartient à l'utilisateur
        if account.user != user:
            logger.warning(f"Tentative d'importation vers le compte {account.id} par utilisateur {user.username} qui n'en est pas le propriétaire.")
            raise ValueError("Vous n'êtes pas autorisé à importer des transactions vers ce compte.")

        with db_transaction.atomic():
            try:
                transactions_data = self.importer.import_transactions(file_content, account, column_mapping)

                for data in transactions_data:
                    amount_for_comparison = data['amount']
                    if data['transaction_type'] == 'OUT':
                        amount_for_comparison = -amount_for_comparison

                    # Filtrer les doublons par l'utilisateur également
                    existing_transaction = Transaction.objects.filter(
                        user=user, # Filtrer par utilisateur
                        date=data['date'],
                        description=data['description'],
                        amount=amount_for_comparison,
                        account=data['account']
                    ).first()

                    if existing_transaction:
                        logger.info(f"Transaction doublon détectée et ignorée lors de l'importation pour utilisateur {user.username}: {data['description']} le {data['date']}")
                        continue

                    transaction_data_for_service = {
                        'date': data['date'],
                        'description': data['description'],
                        'amount': data['amount'],
                        'account': data['account'],
                        'transaction_type': data['transaction_type'],
                        'category': data.get('category'),
                        'tags': data.get('tags', []),
                    }

                    # Passer l'utilisateur à la méthode create_transaction
                    transaction_service.create_transaction(transaction_data_for_service, user)
                    imported_count += 1

            except ValueError as e:
                logger.error(f"Erreur de valeur lors de l'importation des transactions pour utilisateur {user.username}: {e}", exc_info=True)
                raise e
            except Exception as e:
                logger.critical(f"Erreur inattendue lors du traitement d'une transaction importée pour utilisateur {user.username}: {e}", exc_info=True)
                errors.append(f"Erreur lors de l'importation des transactions: {e}")
                raise Exception(f"Erreur lors de l'importation des transactions: {e}")

        if errors:
            raise Exception("Des erreurs sont survenues lors de l'importation: " + "; ".join(errors))

        return imported_count
