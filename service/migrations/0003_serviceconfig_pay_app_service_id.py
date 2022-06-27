# Generated by Django 3.2.13 on 2022-06-23 02:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='serviceconfig',
            name='pay_app_service_id',
            field=models.CharField(default='', help_text='此服务对应的APP服务（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费', max_length=36, verbose_name='余额结算APP服务ID'),
        ),
    ]