# Generated by Django 4.2.5 on 2023-09-19 02:13

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metering', '0004_meteringmonitorwebsite_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DailyStatementMonitorWebsite',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='计费金额')),
                ('payable_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='应付金额')),
                ('trade_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='实付金额')),
                ('payment_status', models.CharField(choices=[('unpaid', '待支付'), ('paid', '已支付'), ('cancelled', '作废')], default='unpaid', max_length=16, verbose_name='支付状态')),
                ('payment_history_id', models.CharField(blank=True, default='', max_length=36, verbose_name='支付记录ID')),
                ('date', models.DateField(help_text='资源使用计量计费的日期', verbose_name='计费日期')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('user_id', models.CharField(blank=True, default='', max_length=36, verbose_name='用户ID')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
            ],
            options={
                'verbose_name': '站点监控日结算单',
                'verbose_name_plural': '站点监控日结算单',
                'db_table': 'daily_statement_mntr_site',
                'ordering': ['-creation_time'],
            },
        ),
    ]