# Generated by Django 4.2.9 on 2024-04-14 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_alert', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScriptFlagModel',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='任务名称')),
                ('start', models.PositiveIntegerField(verbose_name='开始时间戳')),
                ('end', models.PositiveIntegerField(null=True, verbose_name='结束时间戳')),
                ('status', models.CharField(choices=[('running', '运行中'), ('finish', '运行结束'), ('abort', '异常退出')], default='running', max_length=16, verbose_name='运行状态')),
            ],
            options={
                'verbose_name': '定时任务运行标志',
                'verbose_name_plural': '定时任务运行标志',
                'db_table': 'alert_script_flag',
                'ordering': ['-start'],
                'unique_together': {('name', 'start')},
            },
        ),
    ]