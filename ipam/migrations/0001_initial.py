# Generated by Django 4.2.5 on 2023-10-12 09:22

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service', '0003_contacts_datacenter_province_datacenter_contacts'),
    ]

    operations = [
        migrations.CreateModel(
            name='ASN',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField(verbose_name='AS编码')),
                ('name', models.CharField(blank=True, default='', max_length=255, verbose_name='名称')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
            ],
            options={
                'verbose_name': 'AS编号',
                'verbose_name_plural': 'AS编号',
                'db_table': 'ipam_asn',
                'ordering': ('number',),
            },
        ),
        migrations.CreateModel(
            name='OrgVirtualObject',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='名称')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注信息')),
                ('organization', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='service.datacenter', verbose_name='机构')),
            ],
            options={
                'verbose_name': '机构二级',
                'verbose_name_plural': '机构二级',
                'db_table': 'ipam_org_virt_obj',
                'ordering': ('-creation_time',),
            },
        ),
        migrations.CreateModel(
            name='IPv4RangeRecord',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('record_type', models.CharField(choices=[('assign', '分配'), ('recover', '收回'), ('split', '拆分'), ('merge', '合并'), ('add', '添加'), ('change', '修改')], max_length=16, verbose_name='记录类型')),
                ('ip_ranges', models.JSONField(blank=True, default=dict, verbose_name='拆分或合并的IP段')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注信息')),
                ('start_address', models.PositiveIntegerField(verbose_name='起始地址')),
                ('end_address', models.PositiveIntegerField(verbose_name='截止地址')),
                ('mask_len', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(32)], verbose_name='子网掩码长度')),
                ('org_virt_obj', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='ipam.orgvirtualobject', verbose_name='分配给机构虚拟对象')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='操作用户')),
            ],
            options={
                'verbose_name': 'IPv4段操作记录',
                'verbose_name_plural': 'IPv4段操作记录',
                'db_table': 'ipam_ipv4_range_record',
                'ordering': ('-creation_time',),
            },
        ),
        migrations.CreateModel(
            name='IPv4Range',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='', max_length=255, verbose_name='名称')),
                ('status', models.CharField(choices=[('assigned', '已分配'), ('reserved', '预留'), ('wait', '未分配')], default='wait', max_length=16, verbose_name='状态')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('assigned_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='分配时间')),
                ('admin_remark', models.CharField(blank=True, default='', max_length=255, verbose_name='科技网管理员备注信息')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='机构管理员备注信息')),
                ('start_address', models.PositiveIntegerField(verbose_name='起始地址')),
                ('end_address', models.PositiveIntegerField(verbose_name='截止地址')),
                ('mask_len', models.PositiveIntegerField(validators=[django.core.validators.MaxValueValidator(32)], verbose_name='子网掩码长度')),
                ('asn', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='ipam.asn', verbose_name='AS编号')),
                ('org_virt_obj', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='ipam.orgvirtualobject', verbose_name='分配给机构二级')),
            ],
            options={
                'verbose_name': 'IPv4地址段',
                'verbose_name_plural': 'IPv4地址段',
                'db_table': 'ipam_ipv4_range',
                'ordering': ('start_address',),
            },
        ),
        migrations.CreateModel(
            name='IPv4Address',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('admin_remark', models.CharField(blank=True, default='', max_length=255, verbose_name='科技网管理员备注信息')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='机构管理员备注信息')),
                ('ip_address', models.PositiveIntegerField(verbose_name='IP地址')),
                ('ip_range', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='ipam.ipv4range', verbose_name='IP段')),
            ],
            options={
                'verbose_name': 'IPv4地址',
                'verbose_name_plural': 'IPv4地址',
                'db_table': 'ipam_ipv4_addr',
                'ordering': ('ip_address',),
            },
        ),
        migrations.CreateModel(
            name='IPAMUserRole',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_admin', models.BooleanField(default=False, help_text='选中，用户拥有科技网IP管理功能的管理员权限', verbose_name='科技网IP管理员')),
                ('is_readonly', models.BooleanField(default=False, help_text='选中，用户拥有科技网IP管理功能的全局只读权限', verbose_name='IP管理全局只读权限')),
                ('creation_time', models.DateTimeField(verbose_name='创建时间')),
                ('update_time', models.DateTimeField(verbose_name='更新时间')),
                ('organizations', models.ManyToManyField(blank=True, db_table='ipam_user_role_orgs', related_name='+', to='service.datacenter', verbose_name='拥有管理员权限的机构')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': 'IP管理用户角色和权限',
                'verbose_name_plural': 'IP管理用户角色和权限',
                'db_table': 'ipam_user_role',
                'ordering': ('-creation_time',),
            },
        ),
        migrations.AddConstraint(
            model_name='ipv4address',
            constraint=models.UniqueConstraint(fields=('ip_address',), name='unique_ip_address'),
        ),
    ]
