# Generated by Django 4.2.9 on 2024-03-01 09:20

from decimal import Decimal
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0006_order_order_action'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderRefund',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False, verbose_name='退订编号')),
                ('order_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='订单总金额')),
                ('payment_history_id', models.CharField(blank=True, default='', max_length=36, verbose_name='支付记录id')),
                ('status', models.CharField(choices=[('wait', '待退款'), ('refunded', '已退款'), ('failed', '退款失败'), ('cancelled', '取消')], default='wait', max_length=16, verbose_name='退订状态')),
                ('status_desc', models.CharField(blank=True, default='', max_length=255, verbose_name='退订状态描述')),
                ('creation_time', models.DateTimeField(verbose_name='退订时间')),
                ('update_time', models.DateTimeField(verbose_name='修改时间')),
                ('resource_type', models.CharField(choices=[('vm', '云主机'), ('disk', '云硬盘'), ('bucket', '存储桶'), ('scan', '安全扫描')], default='vm', max_length=16, verbose_name='资源类型')),
                ('number', models.PositiveIntegerField(default=1, verbose_name='退订资源数量')),
                ('reason', models.CharField(blank=True, default='', max_length=255, verbose_name='退订原因')),
                ('refund_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='需要退款的金额', max_digits=10, verbose_name='退款金额')),
                ('balance_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='余额退款金额')),
                ('coupon_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='券退款金额')),
                ('refund_history_id', models.CharField(blank=True, default='', max_length=36, verbose_name='退款记录id')),
                ('refunded_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='退款完成时间')),
                ('user_id', models.CharField(blank=True, default='', max_length=36, verbose_name='用户ID')),
                ('username', models.CharField(blank=True, default='', max_length=64, verbose_name='用户名')),
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('vo_name', models.CharField(blank=True, default='', max_length=256, verbose_name='VO组名')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
                ('deleted', models.BooleanField(default=False, verbose_name='删除')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='+', to='order.order', verbose_name='退订订单')),
            ],
            options={
                'verbose_name': '退订退款',
                'verbose_name_plural': '退订退款',
                'db_table': 'order_refund',
                'ordering': ['-creation_time'],
            },
        ),
    ]
