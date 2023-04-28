# Generated by Django 3.2.13 on 2023-04-06 01:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service', '0005_auto_20230404_0143'),
        ('monitor', '0009_auto_20230309_0542'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonitorJobTiDB',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控的TiDB集群名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控的TiDB集群英文名称')),
                ('job_tag', models.CharField(default='', max_length=255, verbose_name='TiDB集群标签名称')),
                ('prometheus', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='Prometheus接口')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remark', models.TextField(blank=True, default='', verbose_name='备注')),
                ('sort_weight', models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值')),
                ('grafana_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Grafana连接')),
                ('dashboard_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Dashboard连接')),
                ('organization', models.ForeignKey(db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='service.datacenter', verbose_name='监控机构')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='monitor.monitorprovider', verbose_name='监控服务配置')),
                ('users', models.ManyToManyField(blank=True, db_constraint=False, db_table='monitor_tidb_users', related_name='_monitor_monitorjobtidb_users_+', to=settings.AUTH_USER_MODEL, verbose_name='管理用户')),
            ],
            options={
                'verbose_name': 'TiDB监控单元',
                'verbose_name_plural': 'TiDB监控单元',
                'db_table': 'monitor_unit_tidb',
                'ordering': ['sort_weight'],
            },
        ),
    ]