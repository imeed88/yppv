# Generated by Django 4.2.3 on 2023-08-21 17:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('apgmp', '0009_alter_order_equipment'),
    ]

    operations = [
        migrations.DeleteModel(
            name='extention',
        ),
        migrations.RenameField(
            model_name='order',
            old_name='extention',
            new_name='extension',
        ),
    ]