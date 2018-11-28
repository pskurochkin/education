# Generated by Django 2.1.3 on 2018-11-25 12:31

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_specialty_place'),
    ]

    operations = [
        migrations.AddField(
            model_name='variant',
            name='applicants',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.IntegerField(), default=[], size=None),
        ),
        migrations.AddField(
            model_name='variant',
            name='rating',
            field=models.FloatField(null=True),
        ),
    ]