# Generated by Django 4.2.8 on 2023-12-26 03:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0007_remove_logsite_organization_remove_logsite_provider_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='logsitetimereqnum',
            name='count',
            field=models.IntegerField(help_text='负数标识数据无效（查询失败的占位记录，便于后补）', verbose_name='请求量'),
        ),
    ]