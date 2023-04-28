# Generated by Django 3.2.13 on 2023-04-10 03:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0005_auto_20230404_0143'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='serviceconfig',
            options={'ordering': ['sort_weight'], 'verbose_name': '服务单元接入配置', 'verbose_name_plural': '服务单元接入配置'},
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='sort_weight',
            field=models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值'),
        ),
    ]