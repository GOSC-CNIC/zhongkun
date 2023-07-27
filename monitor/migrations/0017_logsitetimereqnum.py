# Generated by Django 3.2.13 on 2023-07-26 06:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0016_totalreqnum'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogSiteTimeReqNum',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.PositiveBigIntegerField(verbose_name='统计时间')),
                ('count', models.PositiveIntegerField(verbose_name='请求量')),
                ('site', models.ForeignKey(db_constraint=False, db_index=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='monitor.logsite', verbose_name='日志站点')),
            ],
            options={
                'verbose_name': '日志站点时序请求量',
                'verbose_name_plural': '日志站点时序请求量',
                'db_table': 'log_site_time_req_num',
                'ordering': ['-timestamp'],
            },
        ),
    ]