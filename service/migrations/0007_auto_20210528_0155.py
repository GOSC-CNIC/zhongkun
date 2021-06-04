# Generated by Django 3.1.7 on 2021-05-28 01:55

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('service', '0006_auto_20210407_0307'),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplyDataCenter',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='名称')),
                ('abbreviation', models.CharField(default='', max_length=64, verbose_name='简称')),
                ('independent_legal_person', models.BooleanField(default=True, verbose_name='是否独立法人单位')),
                ('country', models.CharField(default='', max_length=128, verbose_name='国家/地区')),
                ('city', models.CharField(default='', max_length=128, verbose_name='城市')),
                ('postal_code', models.CharField(default='', max_length=32, verbose_name='邮政编码')),
                ('address', models.CharField(default='', max_length=256, verbose_name='单位地址')),
                ('endpoint_vms', models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, unique=True, verbose_name='云主机服务地址url')),
                ('endpoint_object', models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, unique=True, verbose_name='存储服务地址url')),
                ('endpoint_compute', models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, unique=True, verbose_name='计算服务地址url')),
                ('endpoint_monitor', models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, unique=True, verbose_name='检测报警服务地址url')),
                ('creation_time', models.DateTimeField(blank=True, default=None, null=True, verbose_name='创建时间')),
                ('status', models.CharField(choices=[('wait', '待审批'), ('pending', '审批中'), ('reject', '拒绝'), ('pass', '通过')], default='wait', max_length=16, verbose_name='状态')),
                ('desc', models.CharField(blank=True, max_length=255, verbose_name='描述')),
                ('data_center', models.OneToOneField(default=None, help_text='机构加入申请审批通过后对应的机构', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apply_data_center', to='service.datacenter', verbose_name='机构')),
            ],
            options={
                'verbose_name': '机构',
                'verbose_name_plural': '机构',
                'db_table': 'vm_datacenter_apply',
                'ordering': ['creation_time'],
            },
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='contact_address',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='联系人地址'),
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='contact_email',
            field=models.EmailField(blank=True, default='', max_length=254, verbose_name='联系人邮箱'),
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='contact_fixed_phone',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='联系人固定电话'),
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='contact_person',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='联系人名称'),
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='contact_telephone',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='联系人电话'),
        ),
        migrations.AlterField(
            model_name='serviceconfig',
            name='service_type',
            field=models.CharField(choices=[('evcloud', 'EVCloud'), ('openstack', 'OpenStack'), ('vmware', 'VMware')], default='evcloud', max_length=32, verbose_name='服务平台类型'),
        ),
        migrations.AlterField(
            model_name='serviceconfig',
            name='status',
            field=models.CharField(choices=[('enable', '服务中'), ('disable', '停止服务'), ('deleted', '删除')], default='enable', max_length=32, verbose_name='服务状态'),
        ),
        migrations.CreateModel(
            name='ApplyVmService',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('creation_time', models.DateTimeField(auto_now_add=True, verbose_name='申请时间')),
                ('approve_time', models.DateTimeField(auto_now_add=True, verbose_name='审批时间')),
                ('status', models.CharField(choices=[('wait', '待审核'), ('cancel', '取消申请'), ('pending', '审核中'), ('first_pass', '初审通过'), ('first_reject', '初审拒绝'), ('test_failed', '测试未通过'), ('test_pass', '测试通过'), ('reject', '拒绝'), ('pass', '通过')], default='wait', max_length=16, verbose_name='状态')),
                ('longitude', models.FloatField(blank=True, default=0, verbose_name='经度')),
                ('latitude', models.FloatField(blank=True, default=0, verbose_name='纬度')),
                ('name', models.CharField(max_length=255, verbose_name='服务名称')),
                ('region', models.CharField(blank=True, default='', help_text='OpenStack服务区域名称,EVCloud分中心ID', max_length=128, verbose_name='服务区域')),
                ('service_type', models.CharField(choices=[('evcloud', 'EVCloud'), ('openstack', 'OpenStack'), ('vmware', 'VMware')], default='evcloud', max_length=16, verbose_name='服务平台类型')),
                ('endpoint_url', models.CharField(help_text='http(s)://{hostname}:{port}/', max_length=255, unique=True, verbose_name='服务地址url')),
                ('api_version', models.CharField(default='v3', help_text='预留，主要EVCloud使用', max_length=64, verbose_name='API版本')),
                ('username', models.CharField(help_text='用于此服务认证的用户名', max_length=128, verbose_name='用户名')),
                ('password', models.CharField(max_length=255, verbose_name='密码')),
                ('project_name', models.CharField(blank=True, default='', help_text='only required when OpenStack', max_length=128, verbose_name='Project Name')),
                ('project_domain_name', models.CharField(blank=True, default='', help_text='only required when OpenStack', max_length=128, verbose_name='Project Domain Name')),
                ('user_domain_name', models.CharField(blank=True, default='', help_text='only required when OpenStack', max_length=128, verbose_name='User Domain Name')),
                ('remarks', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('need_vpn', models.BooleanField(default=True, verbose_name='是否需要VPN')),
                ('vpn_endpoint_url', models.CharField(help_text='http(s)://{hostname}:{port}/', max_length=255, verbose_name='VPN服务地址url')),
                ('vpn_api_version', models.CharField(default='v3', max_length=64, verbose_name='VPN API版本')),
                ('vpn_username', models.CharField(help_text='用于VPN服务认证的用户名', max_length=128, verbose_name='用户名')),
                ('vpn_password', models.CharField(max_length=255, verbose_name='密码')),
                ('deleted', models.BooleanField(default=False, verbose_name='删除')),
                ('contact_person', models.CharField(blank=True, default='', max_length=128, verbose_name='联系人')),
                ('contact_email', models.EmailField(blank=True, default='', max_length=254, verbose_name='联系人邮箱')),
                ('contact_telephone', models.CharField(blank=True, default='', max_length=16, verbose_name='联系人电话')),
                ('contact_fixed_phone', models.CharField(blank=True, default='', max_length=16, verbose_name='联系人固定电话')),
                ('contact_address', models.CharField(blank=True, default='', max_length=256, verbose_name='联系人地址')),
                ('center_apply', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='service.applydatacenter', verbose_name='数据中心申请')),
                ('data_center', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='service.datacenter', verbose_name='数据中心')),
                ('service', models.OneToOneField(default=None, help_text='服务接入申请审批通过后生成的对应的接入服务', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apply_service', to='service.serviceconfig', verbose_name='接入服务')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='申请用户')),
            ],
            options={
                'verbose_name': 'VM服务接入申请',
                'verbose_name_plural': 'VM服务接入申请',
                'db_table': 'vm_service_apply',
                'ordering': ['-creation_time'],
            },
        ),
        migrations.AlterField(
            model_name='serviceconfig',
            name='password',
            field=models.CharField(max_length=255, verbose_name='密码'),
        ),
        migrations.AlterField(
            model_name='serviceconfig',
            name='vpn_password',
            field=models.CharField(blank=True, default='', max_length=255, verbose_name='VPN服务密码'),
        ),
    ]
