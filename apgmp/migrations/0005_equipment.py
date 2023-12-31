# Generated by Django 4.2.3 on 2023-08-18 13:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apgmp', '0004_remove_order_inventorynr_alter_order_equipment'),
    ]

    operations = [
        migrations.CreateModel(
            name='equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('internref', models.IntegerField()),
                ('description', models.TextField(blank=True, max_length=800)),
                ('functlocation', models.JSONField(blank=True, null=True)),
                ('modelnumber', models.CharField(blank=True, max_length=200)),
                ('manufactserialnr', models.CharField(blank=True, max_length=200)),
                ('inventorynr', models.CharField(blank=True, max_length=25)),
            ],
        ),
    ]
