# Generated by Django 5.2.1 on 2025-06-12 00:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('webapp', '0011_alter_account_options_account_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_shared',
            field=models.BooleanField(default=False, help_text='Si activé, cette catégorie est partagée avec les membres du ménage'),
        ),
    ]
