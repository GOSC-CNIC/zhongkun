# Generated by Django 3.2.5 on 2022-03-10 05:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.CharField(editable=False, max_length=32, primary_key=True, serialize=False, verbose_name='订单编号')),
                ('order_type', models.CharField(choices=[('new', '新购'), ('renewal', '续费'), ('upgrade', '升级'), ('downgrade', '降级'), ('refund', '退款')], default='new', max_length=16, verbose_name='订单类型')),
                ('status', models.CharField(choices=[('paid', '已支付'), ('unpaid', '未支付'), ('cancelled', '作废')], default='paid', max_length=16, verbose_name='订单状态')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='总金额')),
                ('pay_amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=10, verbose_name='实付金额')),
                ('service_id', models.CharField(blank=True, default='', max_length=36, verbose_name='服务id')),
                ('service_name', models.CharField(blank=True, default='', max_length=255, verbose_name='服务名称')),
                ('resource_type', models.CharField(choices=[('vm', '云主机'), ('disk', '云硬盘'), ('bucket', '存储桶')], default='vm', max_length=16, verbose_name='资源类型')),
                ('instance_config', models.JSONField(blank=True, default=dict, verbose_name='资源的规格和配置')),
                ('period', models.IntegerField(blank=True, default=0, verbose_name='订购时长(月)')),
                ('payment_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='支付时间')),
                ('pay_type', models.CharField(choices=[('prepaid', '包年包月'), ('postpaid', '按量计费'), ('quota', '资源配额券')], max_length=16, verbose_name='结算方式')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('user_id', models.CharField(blank=True, default='', max_length=36, verbose_name='用户ID')),
                ('username', models.CharField(blank=True, default='', max_length=64, verbose_name='用户名')),
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('vo_name', models.CharField(blank=True, default='', max_length=256, verbose_name='VO组名')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
            ],
            options={
                'verbose_name': '订单',
                'verbose_name_plural': '订单',
                'db_table': 'order',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource_type', models.CharField(choices=[('vm', '云主机'), ('disk', '云硬盘'), ('bucket', '存储桶')], max_length=16, verbose_name='资源类型')),
                ('instance_id', models.CharField(blank=True, default='', max_length=36, verbose_name='资源实例id')),
                ('instance_status', models.CharField(choices=[('wait', '待创建'), ('success', '创建成功'), ('failed', '创建失败')], default='wait', max_length=16, verbose_name='资源创建结果')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='resource_set', to='order.order', verbose_name='订单')),
            ],
            options={
                'verbose_name': '订单资源',
                'verbose_name_plural': '订单资源',
                'db_table': 'order_resource',
                'ordering': ['-creation_time'],
            },
        ),
    ]
