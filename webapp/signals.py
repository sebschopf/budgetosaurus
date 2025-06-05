# webapp/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import Transaction # Importez le modèle Transaction depuis le même dossier

@receiver(pre_save, sender=Transaction)
def normalize_transaction_amount(sender, instance, **kwargs):
    """
    Normalise le montant de la transaction avant la sauvegarde en fonction de son type.
    Si le type est 'OUT' (Dépense) et le montant est positif, il est rendu négatif.
    Si le type est 'IN' (Revenu) et le montant est négatif, il est rendu positif (valeur absolue).
    """
    if instance.transaction_type == 'OUT' and instance.amount > 0:
        instance.amount = -instance.amount
    elif instance.transaction_type == 'IN' and instance.amount < 0:
        instance.amount = abs(instance.amount)

