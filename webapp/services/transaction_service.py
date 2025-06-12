from django.db import transaction as db_transaction
from django.db.models import Sum
from webapp.models import Transaction, Account, Category, Fund, CategorizationRule, Tag
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
    def create_transaction(self, data: dict, user) -> Transaction:
        """
        Crée et sauvegarde une nouvelle transaction pour un utilisateur donné.
        Met à jour le solde du fonds budgétaire associé si pertinent.
        Apprend de la transaction pour les règles de catégorisation de cet utilisateur.
        """
        with db_transaction.atomic():
            # Assurez-vous que la transaction est liée à l'utilisateur
            data['user'] = user

            # Extraire les tags de 'data' car ils sont un ManyToManyField
            tags_data = data.pop('tags', [])
            transaction = Transaction.objects.create(**data)
            transaction.tags.set(tags_data)

            # Logique de mise à jour des fonds
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount), user)
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (dépense) pour utilisateur {user.username}: soustraction de {abs(transaction.amount)}.")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)

                elif transaction.transaction_type == 'IN':
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount), user)
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (revenu individuel) pour utilisateur {user.username}: ajout de {abs(transaction.amount)}.")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)

            # Apprendre de cette transaction pour la catégorisation automatique
            self._update_categorization_rule(transaction, user)

            return transaction

    def update_transaction(self, transaction: Transaction, data: dict, user) -> Transaction:
        """
        Met à jour une transaction existante pour un utilisateur donné.
        """
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

            transaction.user = user
            transaction.save()
            if tags_data is not None:
                transaction.tags.set(tags_data)

            # Logique d'ajustement des fonds lors d'une mise à jour
            # 1. Annuler l'impact de l'ancienne transaction
            if original_category and original_type != 'TRF' and original_category.is_fund_managed:
                if original_type == 'OUT':
                    try:
                        Fund.objects.add_funds_to_category(original_category, abs(original_amount_normalized), user)
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancienne dépense) pour utilisateur {user.username}.")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancienne dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                elif original_type == 'IN' and original_account.account_type == 'INDIVIDUAL':
                    try:
                        Fund.objects.subtract_funds_from_category(original_category, abs(original_amount_normalized), user)
                        logger.info(f"Fonds '{original_category.name}' ajusté (annulation ancien revenu individuel) pour utilisateur {user.username}.")
                    except Exception as e:
                        logger.error(f"Erreur lors de l'annulation du fonds (ancien revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)

            # 2. Appliquer l'impact de la nouvelle transaction
            if transaction.category and transaction.transaction_type != 'TRF' and transaction.category.is_fund_managed:
                if transaction.transaction_type == 'OUT':
                    try:
                        Fund.objects.subtract_funds_from_category(transaction.category, abs(transaction.amount), user)
                        logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouvelle dépense) pour utilisateur {user.username}.")
                    except Exception as e:
                        logger.error(f"Erreur lors de la mise à jour du fonds (nouvelle dépense) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)
                elif transaction.transaction_type == 'IN':
                    if transaction.account.account_type == 'INDIVIDUAL':
                        try:
                            Fund.objects.add_funds_to_category(transaction.category, abs(transaction.amount), user)
                            logger.info(f"Fonds '{transaction.category.name}' mis à jour (nouveau revenu individuel) pour utilisateur {user.username}.")
                        except Exception as e:
                            logger.error(f"Erreur lors de la mise à jour du fonds (nouvel revenu individuel) pour la transaction {transaction.id} et utilisateur {user.username}: {e}", exc_info=True)

            # Apprendre de cette transaction mise à jour
            self._update_categorization_rule(transaction, user)

            return transaction

    def _update_categorization_rule(self, transaction: Transaction, user):
        """
        Crée ou met à jour une règle de catégorisation basée sur une transaction
        pour un utilisateur spécifique.
        """
        if not transaction.description or not transaction.category:
            logger.debug(f"Pas de mise à jour de règle de catégorisation pour transaction {transaction.id}: description ou catégorie manquante.")
            return

        try:
            rule, created = CategorizationRule.objects.get_or_create(
                user=user,
                description_pattern=transaction.description,
                defaults={
                    'suggested_category': transaction.category,
                    'hit_count': 1,
                    'last_applied_at': timezone.now()
                }
            )
            if not created:
                if rule.suggested_category != transaction.category:
                    logger.info(f"Mise à jour de la catégorie suggérée pour la règle '{rule.description_pattern}' pour utilisateur {user.username}.")
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

    def get_latest_transactions(self, user, limit: int = 10) -> list[Transaction]:
        """
        Récupère les N dernières transactions pour un utilisateur donné.
        """
        return Transaction.objects.filter(user=user).select_related('category', 'account').prefetch_related('tags').order_by('-date', '-created_at')[:limit]

    def suggest_categorization(self, description: str, user):
        """
        Suggère une catégorie et des tags basés sur la description de la transaction,
        en utilisant le fuzzy matching si aucune correspondance exacte n'est trouvée,
        pour les règles propres à l'utilisateur.
        """
        if not description:
            return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        exact_rule = CategorizationRule.objects.filter(user=user, description_pattern=description).first()

        if exact_rule and exact_rule.suggested_category:
            rule_to_use = exact_rule
            logger.debug(f"Suggestion exacte trouvée pour '{description}' pour utilisateur {user.username}.")
        else:
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
                logger.debug(f"Suggestion floue trouvée pour '{description}' pour utilisateur {user.username}.")
            else:
                logger.debug(f"Aucune suggestion trouvée pour '{description}' pour utilisateur {user.username}.")
                return {'category_id': None, 'category_name': None, 'subcategory_id': None, 'subcategory_name': None, 'tag_ids': [], 'tag_names': []}

        if rule_to_use and rule_to_use.suggested_category:
            suggested_category = rule_to_use.suggested_category
            suggested_tags = list(rule_to_use.suggested_tags.all())

            try:
                rule_to_use.hit_count += 1
                rule_to_use.last_applied_at = timezone.now()
                rule_to_use.save()
                logger.debug(f"Règle de catégorisation '{rule_to_use.description_pattern}' pour utilisateur {user.username} hit_count incrémenté.")
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
