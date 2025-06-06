# Generated by Django 5.2.1 on 2025-06-04 21:34

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nom du compte')),
                ('currency', models.CharField(default='CHF', max_length=3, verbose_name='Devise')),
                ('initial_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=15, verbose_name='Solde initial')),
            ],
            options={
                'verbose_name': 'Compte Bancaire',
                'verbose_name_plural': 'Comptes Bancaires',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='Nom du Tag')),
                ('description', models.TextField(blank=True, verbose_name='Description du Tag')),
                ('last_used_at', models.DateTimeField(auto_now_add=True, verbose_name='Dernière utilisation')),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nom')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('last_used_at', models.DateTimeField(auto_now_add=True, verbose_name='Dernière utilisation')),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='webapp.category', verbose_name='Catégorie parente')),
            ],
            options={
                'verbose_name': 'Catégorie',
                'verbose_name_plural': 'Catégories',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Fund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=15, verbose_name='Solde actuel du fonds')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('category', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='fund', to='webapp.category', verbose_name='Catégorie de fonds')),
            ],
            options={
                'verbose_name': 'Fonds Budgétaire',
                'verbose_name_plural': 'Fonds Budgétaires',
                'ordering': ['category__name'],
            },
        ),
        migrations.CreateModel(
            name='SavingGoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name="Nom de l'objectif")),
                ('target_amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant Cible')),
                ('current_amount_saved', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='Montant Actuel Mis de Côté')),
                ('target_date', models.DateField(verbose_name='Date Cible')),
                ('status', models.CharField(choices=[('OU', 'Ouvert'), ('AT', 'Atteint'), ('AN', 'Annulé')], default='OU', max_length=2, verbose_name='Statut')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='saving_goals', to='webapp.category', verbose_name='Catégorie liée (optionnel)')),
            ],
            options={
                'verbose_name': "Objectif d'Épargne",
                'verbose_name_plural': "Objectifs d'Épargne",
                'ordering': ['target_date', 'status'],
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(default=django.utils.timezone.now, verbose_name='Date')),
                ('description', models.CharField(max_length=255, verbose_name='Description')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant')),
                ('transaction_type', models.CharField(choices=[('IN', 'Revenu'), ('OUT', 'Dépense'), ('TRF', 'Transfert')], default='OUT', max_length=3, verbose_name='Type de transaction')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Créé le')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Mis à jour le')),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='webapp.account', verbose_name='Compte')),
                ('category', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='webapp.category', verbose_name='Catégorie')),
                ('tags', models.ManyToManyField(blank=True, related_name='transactions', to='webapp.tag', verbose_name='Tags')),
            ],
            options={
                'verbose_name': 'Transaction',
                'verbose_name_plural': 'Transactions',
                'ordering': ['-date', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Budget',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant Budgété')),
                ('period_type', models.CharField(choices=[('M', 'Mensuel'), ('Y', 'Annuel')], default='M', max_length=1, verbose_name='Type de Période')),
                ('start_date', models.DateField(verbose_name='Date de Début')),
                ('end_date', models.DateField(blank=True, null=True, verbose_name='Date de Fin (optionnel)')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='budgets', to='webapp.category', verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': 'Budget',
                'verbose_name_plural': 'Budgets',
                'ordering': ['start_date', 'category__name'],
                'unique_together': {('category', 'period_type', 'start_date')},
            },
        ),
    ]
