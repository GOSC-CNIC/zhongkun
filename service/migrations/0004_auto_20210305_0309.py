# Generated by Django 3.1.7 on 2021-03-05 03:09

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service', '0003_auto_20210204_0708'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='datacenter',
            name='users',
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='users',
            field=models.ManyToManyField(blank=True, related_name='service_set', to=settings.AUTH_USER_MODEL, verbose_name='用户'),
        ),
    ]