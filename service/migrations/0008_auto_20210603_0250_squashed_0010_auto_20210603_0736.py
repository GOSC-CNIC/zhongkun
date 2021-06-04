# Generated by Django 3.2 on 2021-06-03 07:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('service', '0007_auto_20210528_0155'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ApplyOrganization',
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
                ('creation_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('status', models.CharField(choices=[('wait', '待审批'), ('cancel', '取消申请'), ('pending', '审批中'), ('reject', '拒绝'), ('pass', '通过')], default='wait', max_length=16, verbose_name='状态')),
                ('desc', models.CharField(blank=True, max_length=255, verbose_name='描述')),
                ('logo_url', models.CharField(blank=True, default='', max_length=256, verbose_name='LOGO url')),
                ('certification_url', models.CharField(blank=True, default='', max_length=256, verbose_name='机构认证代码url')),
            ],
            options={
                'verbose_name': '机构加入申请',
                'verbose_name_plural': '机构加入申请',
                'db_table': 'organization_apply',
                'ordering': ['creation_time'],
            },
        ),
        migrations.RemoveField(
            model_name='applyvmservice',
            name='center_apply',
        ),
        migrations.AddField(
            model_name='applyvmservice',
            name='logo_url',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='LOGO url'),
        ),
        migrations.AlterField(
            model_name='datacenter',
            name='endpoint_compute',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='计算服务地址url'),
        ),
        migrations.AlterField(
            model_name='datacenter',
            name='endpoint_monitor',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='检测报警服务地址url'),
        ),
        migrations.AlterField(
            model_name='datacenter',
            name='endpoint_object',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='存储服务地址url'),
        ),
        migrations.AlterField(
            model_name='datacenter',
            name='endpoint_vms',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='云主机服务地址url'),
        ),
        migrations.DeleteModel(
            name='ApplyDataCenter',
        ),
        migrations.AddField(
            model_name='applyorganization',
            name='data_center',
            field=models.OneToOneField(blank=True, default=None, help_text='机构加入申请审批通过后对应的机构', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='apply_data_center', to='service.datacenter', verbose_name='机构'),
        ),
        migrations.AddField(
            model_name='applyorganization',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='申请用户'),
        ),
        migrations.AddField(
            model_name='applyorganization',
            name='deleted',
            field=models.BooleanField(default=False, verbose_name='删除'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='abbreviation',
            field=models.CharField(default='', max_length=64, verbose_name='简称'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='address',
            field=models.CharField(default='', max_length=256, verbose_name='单位地址'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='certification_url',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='机构认证代码url'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='city',
            field=models.CharField(default='', max_length=128, verbose_name='城市'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='country',
            field=models.CharField(default='', max_length=128, verbose_name='国家/地区'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='independent_legal_person',
            field=models.BooleanField(default=True, verbose_name='是否独立法人单位'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='logo_url',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='LOGO url'),
        ),
        migrations.AddField(
            model_name='datacenter',
            name='postal_code',
            field=models.CharField(default='', max_length=32, verbose_name='邮政编码'),
        ),
        migrations.AddField(
            model_name='serviceconfig',
            name='logo_url',
            field=models.CharField(blank=True, default='', max_length=256, verbose_name='LOGO url'),
        ),
        migrations.AlterField(
            model_name='applyorganization',
            name='endpoint_compute',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='计算服务地址url'),
        ),
        migrations.AlterField(
            model_name='applyorganization',
            name='endpoint_monitor',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='检测报警服务地址url'),
        ),
        migrations.AlterField(
            model_name='applyorganization',
            name='endpoint_object',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='存储服务地址url'),
        ),
        migrations.AlterField(
            model_name='applyorganization',
            name='endpoint_vms',
            field=models.CharField(blank=True, default=None, help_text='http(s)://{hostname}:{port}/', max_length=255, null=True, verbose_name='云主机服务地址url'),
        ),
    ]
