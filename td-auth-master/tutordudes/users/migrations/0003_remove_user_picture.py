# Generated by Django 2.2 on 2021-04-25 00:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20210420_1538'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='picture',
        ),
    ]