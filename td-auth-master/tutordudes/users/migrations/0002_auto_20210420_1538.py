# Generated by Django 2.2 on 2021-04-20 22:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='stripe_customer_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
