# Generated by Django 4.2.11 on 2024-04-01 07:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_netflow', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chartmodel',
            name='remark',
            field=models.TextField(blank=True, default='', null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='menucategorymodel',
            name='remark',
            field=models.TextField(blank=True, default='', null=True, verbose_name='备注'),
        ),
        migrations.AlterField(
            model_name='menumodel',
            name='remark',
            field=models.TextField(blank=True, default='', null=True, verbose_name='备注'),
        ),
    ]