# Generated by Django 5.1.5 on 2025-03-09 02:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0012_alter_paciente_number'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctor',
            name='number',
            field=models.CharField(max_length=14),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='number',
            field=models.CharField(blank=True, max_length=14, null=True),
        ),
    ]
