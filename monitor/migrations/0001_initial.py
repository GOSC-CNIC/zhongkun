# Generated by Django 4.2.4 on 2023-08-29 08:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='LogSite',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, verbose_name='日志单元站点名称')),
                ('name_en', models.CharField(default='', max_length=128, verbose_name='日志单元英文名称')),
                ('log_type', models.CharField(choices=[('http', 'HTTP'), ('nat', 'NAT')], default='http', max_length=16, verbose_name='日志类型')),
                ('job_tag', models.CharField(default='', help_text='Loki日志中对应的job标识，模板xxx_log', max_length=64, verbose_name='网站日志单元标识')),
                ('sort_weight', models.IntegerField(help_text='值越小排序越靠前', verbose_name='排序值')),
                ('desc', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modification', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
            ],
            options={
                'verbose_name': '日志单元',
                'verbose_name_plural': '日志单元',
                'db_table': 'log_site',
                'ordering': ['sort_weight'],
            },
        ),
        migrations.CreateModel(
            name='LogSiteTimeReqNum',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.PositiveBigIntegerField(verbose_name='统计时间')),
                ('count', models.PositiveIntegerField(verbose_name='请求量')),
            ],
            options={
                'verbose_name': '日志单元时序请求量',
                'verbose_name_plural': '日志单元时序请求量',
                'db_table': 'log_site_time_req_num',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='LogSiteType',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='对象存储、一体云', max_length=64, unique=True, verbose_name='日志网站类别名称')),
                ('name_en', models.CharField(default='', max_length=128, verbose_name='英文名称')),
                ('sort_weight', models.IntegerField(help_text='值越小排序越靠前', verbose_name='排序值')),
                ('desc', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('modification', models.DateTimeField(auto_now=True, verbose_name='修改时间')),
            ],
            options={
                'verbose_name': '日志单元类别',
                'verbose_name_plural': '日志单元类别',
                'db_table': 'log_site_type',
                'ordering': ['sort_weight'],
            },
        ),
        migrations.CreateModel(
            name='MonitorJobCeph',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控的CEPH集群名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控的CEPH集群英文名称')),
                ('job_tag', models.CharField(default='', help_text='模板：xxx_ceph_metric', max_length=255, verbose_name='CEPH集群标签名称')),
                ('prometheus', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='Prometheus接口')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remark', models.TextField(blank=True, default='', verbose_name='备注')),
                ('sort_weight', models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值')),
                ('grafana_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Grafana连接')),
                ('dashboard_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Dashboard连接')),
            ],
            options={
                'verbose_name': 'Ceph监控单元',
                'verbose_name_plural': 'Ceph监控单元',
                'db_table': 'monitor_monitorjobceph',
                'ordering': ['sort_weight'],
            },
        ),
        migrations.CreateModel(
            name='MonitorJobServer',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控的主机集群名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控的主机集群英文名称')),
                ('job_tag', models.CharField(default='', help_text='模板：xxx_node_metric', max_length=255, verbose_name='主机集群标签名称')),
                ('prometheus', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='Prometheus接口')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remark', models.TextField(blank=True, default='', verbose_name='备注')),
                ('sort_weight', models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值')),
                ('grafana_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Grafana连接')),
                ('dashboard_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Dashboard连接')),
            ],
            options={
                'verbose_name': '服务器监控单元',
                'verbose_name_plural': '服务器监控单元',
                'db_table': 'monitor_monitorjobserver',
                'ordering': ['sort_weight'],
            },
        ),
        migrations.CreateModel(
            name='MonitorJobTiDB',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控的TiDB集群名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控的TiDB集群英文名称')),
                ('job_tag', models.CharField(default='', help_text='模板：xxx_tidb_metric', max_length=255, verbose_name='TiDB集群标签名称')),
                ('prometheus', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='Prometheus接口')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remark', models.TextField(blank=True, default='', verbose_name='备注')),
                ('sort_weight', models.IntegerField(default=0, help_text='值越小排序越靠前', verbose_name='排序值')),
                ('grafana_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Grafana连接')),
                ('dashboard_url', models.CharField(blank=True, default='', max_length=255, verbose_name='Dashboard连接')),
                ('version', models.CharField(blank=True, default='', help_text='xx.xx.xx', max_length=32, verbose_name='TiDB版本')),
            ],
            options={
                'verbose_name': 'TiDB监控单元',
                'verbose_name_plural': 'TiDB监控单元',
                'db_table': 'monitor_unit_tidb',
                'ordering': ['sort_weight'],
            },
        ),
        migrations.CreateModel(
            name='MonitorJobVideoMeeting',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='科技云会服务节点院所名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='科技云会服务节点院所英文名称')),
                ('job_tag', models.CharField(default='', max_length=255, verbose_name='标签名称')),
                ('ips', models.CharField(default='', help_text='多个ip用“;”分割', max_length=255, verbose_name='ipv4地址')),
                ('longitude', models.FloatField(blank=True, default=0, verbose_name='经度')),
                ('latitude', models.FloatField(blank=True, default=0, verbose_name='纬度')),
                ('prometheus', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='Prometheus接口')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('remark', models.CharField(blank=True, default='', max_length=1024, verbose_name='备注')),
            ],
            options={
                'verbose_name': '科技云会视频会议监控工作节点',
                'verbose_name_plural': '科技云会视频会议监控工作节点',
                'db_table': 'monitor_monitorjobvideomeeting',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='MonitorProvider',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='监控服务名称')),
                ('name_en', models.CharField(default='', max_length=255, verbose_name='监控服务英文名称')),
                ('endpoint_url', models.CharField(default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='查询接口')),
                ('username', models.CharField(blank=True, default='', help_text='用于此服务认证的用户名', max_length=128, verbose_name='认证用户名')),
                ('password', models.CharField(blank=True, default='', max_length=255, verbose_name='认证密码')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('receive_url', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='接收接口')),
                ('bucket_service_name', models.CharField(blank=True, default='', max_length=128, verbose_name='存储桶所在对象存储服务名称')),
                ('bucket_service_url', models.CharField(blank=True, default='', help_text='http(s)://example.cn/', max_length=255, verbose_name='存储桶所在对象存储服务地址')),
                ('bucket_name', models.CharField(blank=True, default='', max_length=128, verbose_name='存储桶名称')),
                ('remark', models.TextField(blank=True, default='', verbose_name='备注')),
            ],
            options={
                'verbose_name': '监控数据查询提供者服务',
                'verbose_name_plural': '监控数据查询提供者服务',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='MonitorWebsite',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=255, verbose_name='网站名称')),
                ('url', models.URLField(default='', help_text='http(s)://xxx.xxx', max_length=2048, verbose_name='要监控的网址')),
                ('url_hash', models.CharField(default='', max_length=64, verbose_name='网址hash值')),
                ('creation', models.DateTimeField(verbose_name='创建时间')),
                ('modification', models.DateTimeField(verbose_name='修改时间')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('is_attention', models.BooleanField(default=False, verbose_name='特别关注')),
                ('is_tamper_resistant', models.BooleanField(default=False, verbose_name='防篡改')),
                ('scheme', models.CharField(default='', help_text='https|tcp://', max_length=32, verbose_name='协议')),
                ('hostname', models.CharField(default='', help_text='hostname:8000', max_length=255, verbose_name='域名[:端口]')),
                ('uri', models.CharField(default='', help_text='/a/b?query=123#test', max_length=1024, verbose_name='URI')),
            ],
            options={
                'verbose_name': '网站监控',
                'verbose_name_plural': '网站监控',
                'db_table': 'monitor_website',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='MonitorWebsiteTask',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.CharField(default='', max_length=2048, verbose_name='要监控的网址')),
                ('url_hash', models.CharField(default='', max_length=64, unique=True, verbose_name='网址hash值')),
                ('creation', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('is_tamper_resistant', models.BooleanField(default=False, verbose_name='防篡改')),
            ],
            options={
                'verbose_name': '网站监控任务',
                'verbose_name_plural': '网站监控任务',
                'db_table': 'monitor_website_task',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='MonitorWebsiteVersion',
            fields=[
                ('id', models.IntegerField(default=1, primary_key=True, serialize=False)),
                ('version', models.BigIntegerField(default=1, help_text='用于区分网站监控任务表是否有变化', verbose_name='监控任务版本号')),
                ('creation', models.DateTimeField(verbose_name='创建时间')),
                ('modification', models.DateTimeField(verbose_name='修改时间')),
            ],
            options={
                'verbose_name': '网站监控任务版本',
                'verbose_name_plural': '网站监控任务版本',
                'db_table': 'monitor_website_version_provider',
                'ordering': ['-creation'],
            },
        ),
        migrations.CreateModel(
            name='TotalReqNum',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('req_num', models.IntegerField(default=0, verbose_name='服务总请求数')),
                ('until_time', models.DateTimeField(verbose_name='截止到时间')),
                ('creation', models.DateTimeField(verbose_name='创建时间')),
                ('modification', models.DateTimeField(verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '本服务和对象存储总请求数',
                'verbose_name_plural': '本服务和对象存储总请求数',
                'db_table': 'total_req_num',
                'ordering': ['creation'],
            },
        ),
        migrations.CreateModel(
            name='WebsiteDetectionPoint',
            fields=[
                ('id', models.CharField(blank=True, editable=False, max_length=36, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='', max_length=128, verbose_name='监控探测点名称')),
                ('name_en', models.CharField(default='', max_length=128, verbose_name='监控探测点英文名称')),
                ('creation', models.DateTimeField(verbose_name='创建时间')),
                ('modification', models.DateTimeField(verbose_name='修改时间')),
                ('remark', models.CharField(blank=True, default='', max_length=255, verbose_name='备注')),
                ('enable', models.BooleanField(default=True, verbose_name='是否启用')),
                ('provider', models.ForeignKey(db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='monitor.monitorprovider', verbose_name='监控查询服务配置信息')),
            ],
            options={
                'verbose_name': '网站监控探测点',
                'verbose_name_plural': '网站监控探测点',
                'db_table': 'website_detection_point',
                'ordering': ['-creation'],
            },
        ),
    ]
