# Generated by Django 3.2.13 on 2023-05-05 01:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metering', '0003_auto_20220907_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='meteringobjectstorage',
            name='storage_byte',
            field=models.BigIntegerField(blank=True, default=0, help_text='计量时存储桶的存储容量字节数', verbose_name='存储容量(字节)'),
        ),
    ]