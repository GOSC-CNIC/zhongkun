# Generated by Django 4.2.5 on 2023-11-02 06:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0006_remove_serviceconfig_data_center_and_more'),
        ('storage', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='objectsservice',
            name='org_data_center',
            field=models.ForeignKey(db_constraint=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='service.orgdatacenter', verbose_name='数据中心'),
        ),
    ]