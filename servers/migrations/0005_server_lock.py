# Generated by Django 3.2.5 on 2021-08-27 07:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('servers', '0004_auto_20210723_0605'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='lock',
            field=models.CharField(choices=[('free', '无锁'), ('lock-delete', '锁定删除'), ('lock-operation', '锁定所有操作，只允许读')], default='free', help_text='加锁锁定云主机，防止误操作', max_length=16, verbose_name='锁'),
        ),
    ]
