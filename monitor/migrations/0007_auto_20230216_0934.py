# Generated by Django 3.2.13 on 2023-02-16 09:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0004_alter_serviceconfig_endpoint_url'),
        ('monitor', '0006_monitorwebsite'),
    ]

    operations = [
        migrations.AddField(
            model_name='monitorjobceph',
            name='organization',
            field=models.ForeignKey(db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='service.datacenter', verbose_name='监控机构'),
        ),
        migrations.AddField(
            model_name='monitorjobserver',
            name='organization',
            field=models.ForeignKey(db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='service.datacenter', verbose_name='监控机构'),
        ),
    ]