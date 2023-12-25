# Generated by Django 4.2.4 on 2023-08-29 08:00

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DailyStatementDisk',
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
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('vo_name', models.CharField(blank=True, default='', max_length=255, verbose_name='VO组名')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
            ],
            options={
                'verbose_name': '云硬盘每日账单',
                'verbose_name_plural': '云硬盘每日账单',
                'db_table': 'daily_statement_disk',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='DailyStatementObjectStorage',
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
                'verbose_name': '对象存储每日账单',
                'verbose_name_plural': '对象存储每日账单',
                'db_table': 'daily_statement_storage',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='DailyStatementServer',
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
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('vo_name', models.CharField(blank=True, default='', max_length=255, verbose_name='VO组名')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
            ],
            options={
                'verbose_name': '云主机每日账单',
                'verbose_name_plural': '云主机每日账单',
                'db_table': 'daily_statement_server',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='MeteringDisk',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='计费金额')),
                ('trade_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='应付金额')),
                ('daily_statement_id', models.CharField(default='', max_length=36, verbose_name='日结算单ID')),
                ('disk_id', models.CharField(max_length=36, verbose_name='云硬盘ID')),
                ('date', models.DateField(help_text='计量的资源使用量的所属日期', verbose_name='日期')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('user_id', models.CharField(blank=True, default='', max_length=36, verbose_name='用户ID')),
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
                ('size_hours', models.FloatField(blank=True, default=0, help_text='云硬盘Gib Hour数', verbose_name='云硬盘GiB Hour')),
                ('snapshot_hours', models.FloatField(blank=True, default=0, help_text='云硬盘快照GiB小时数', verbose_name='快照GiB Hour')),
                ('pay_type', models.CharField(choices=[('prepaid', '包年包月'), ('postpaid', '按量计费'), ('quota', '资源配额券')], max_length=16, verbose_name='云硬盘付费方式')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
                ('vo_name', models.CharField(blank=True, default='', max_length=255, verbose_name='VO组名')),
            ],
            options={
                'verbose_name': '云硬盘资源计量',
                'verbose_name_plural': '云硬盘资源计量',
                'db_table': 'metering_disk',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='MeteringObjectStorage',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='计费金额')),
                ('trade_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='应付金额')),
                ('daily_statement_id', models.CharField(default='', max_length=36, verbose_name='日结算单ID')),
                ('user_id', models.CharField(blank=True, max_length=36, verbose_name='用户ID')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
                ('storage_bucket_id', models.CharField(default='', help_text='对象存储中间件存储桶实例id', max_length=36, verbose_name='存储桶实例ID')),
                ('bucket_name', models.CharField(max_length=63, verbose_name='存储桶名称')),
                ('date', models.DateField(help_text='计量的资源使用量的所属日期', verbose_name='日期')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('storage', models.FloatField(blank=True, default=0, help_text='存储桶的存储容量GiB小时数', verbose_name='存储容量GiB*hours')),
                ('storage_byte', models.BigIntegerField(blank=True, default=0, help_text='计量时存储桶的存储容量字节数', verbose_name='存储容量(字节)')),
                ('downstream', models.FloatField(blank=True, default=0, help_text='存储桶的下行流量GiB', verbose_name='下行流量GiB')),
                ('replication', models.FloatField(blank=True, default=0, help_text='存储桶的同步流量GiB', verbose_name='同步流量GiB')),
                ('get_request', models.IntegerField(default=0, help_text='存储桶的get请求次数', verbose_name='get请求次数')),
                ('put_request', models.IntegerField(default=0, help_text='存储桶的put请求次数', verbose_name='put请求次数')),
                ('billed_network_flow', models.FloatField(blank=True, default=0, help_text='存储桶的计费流量GiB', verbose_name='计费流量GiB')),
                ('unbilled_network_flow', models.FloatField(blank=True, default=0, help_text='存储桶的非计费流量GiB', verbose_name='非计费流量GiB')),
            ],
            options={
                'verbose_name': '对象存储资源计量',
                'verbose_name_plural': '对象存储资源计量',
                'db_table': 'metering_object_storage',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.CreateModel(
            name='MeteringServer',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('original_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='计费金额')),
                ('trade_amount', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=10, verbose_name='应付金额')),
                ('daily_statement_id', models.CharField(default='', max_length=36, verbose_name='日结算单ID')),
                ('server_id', models.CharField(max_length=36, verbose_name='云服务器ID')),
                ('date', models.DateField(help_text='计量的资源使用量的所属日期', verbose_name='日期')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('user_id', models.CharField(blank=True, default='', max_length=36, verbose_name='用户ID')),
                ('vo_id', models.CharField(blank=True, default='', max_length=36, verbose_name='VO组ID')),
                ('owner_type', models.CharField(choices=[('user', '用户'), ('vo', 'VO组')], max_length=8, verbose_name='所有者类型')),
                ('cpu_hours', models.FloatField(blank=True, default=0, help_text='云服务器的CPU Hour数', verbose_name='CPU Hour')),
                ('ram_hours', models.FloatField(blank=True, default=0, help_text='云服务器的内存Gib Hour数', verbose_name='内存GiB Hour')),
                ('disk_hours', models.FloatField(blank=True, default=0, help_text='云服务器的系统盘Gib Hour数', verbose_name='系统盘GiB Hour')),
                ('public_ip_hours', models.FloatField(blank=True, default=0, help_text='云服务器的公网IP Hour数', verbose_name='IP Hour')),
                ('snapshot_hours', models.FloatField(blank=True, default=0, help_text='云服务器的快照小时数', verbose_name='快照GiB Hour')),
                ('upstream', models.FloatField(blank=True, default=0, help_text='云服务器的上行流量Gib', verbose_name='上行流量GiB')),
                ('downstream', models.FloatField(blank=True, default=0, help_text='云服务器的下行流量Gib', verbose_name='下行流量GiB')),
                ('pay_type', models.CharField(choices=[('prepaid', '包年包月'), ('postpaid', '按量计费'), ('quota', '资源配额券')], max_length=16, verbose_name='云服务器付费方式')),
                ('username', models.CharField(blank=True, default='', max_length=128, verbose_name='用户名')),
                ('vo_name', models.CharField(blank=True, default='', max_length=255, verbose_name='VO组名')),
            ],
            options={
                'verbose_name': '云主机资源计量',
                'verbose_name_plural': '云主机资源计量',
                'db_table': 'metering_server',
                'ordering': ['-creation_time'],
            },
        ),
    ]
