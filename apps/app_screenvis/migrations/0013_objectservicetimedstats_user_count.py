# Generated by Django 4.2.9 on 2024-07-15 07:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_screenvis', '0012_serverservicetimedstats_pri_ip_count_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='objectservicetimedstats',
            name='user_count',
            field=models.IntegerField(blank=True, default=0, verbose_name='用户数'),
        ),
    ]