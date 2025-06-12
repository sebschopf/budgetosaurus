from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('CH', 'Compte Courant'),
        ('EP', 'Compte d\'Épargne'),
        ('CR', 'Compte de Crédit'),
        ('ES', 'Espèces'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='accounts')
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=2, choices=ACCOUNT_TYPES, default='CH')
    currency = models.CharField(max_length=3, default='CHF')
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Indique si le compte est partagé avec le ménage
    is_shared = models.BooleanField(
        default=False, 
        help_text="Si activé, ce compte est partagé avec les membres du ménage"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'name']

    def __str__(self):
        shared_status = " (Partagé)" if self.is_shared else ""
        return f"{self.name}{shared_status} ({self.get_account_type_display()}) - {self.user.username}"
