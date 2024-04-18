from datetime import datetime
import ipaddress

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone as dj_timezone
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from utils.model import UuidModel, get_encryptor
from utils.iprestrict import convert_iprange


class ScreenConfig(models.Model):
    class ConfigName(models.TextChoices):
        ORG_NAME = 'org_name', _('机构名称')
        ORG_NAME_EN = 'org_name_en', _('机构英文名称')

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(verbose_name=_('配置名称'), max_length=32, choices=ConfigName.choices)
    value = models.CharField(verbose_name=_('配置内容'), max_length=255, default='')
    remark = models.CharField(verbose_name=_('备注'), blank=True, max_length=255)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'screenvis_config'
        ordering = ['creation_time']
        verbose_name = _('配置')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('name',), name='unique_config_name')
        ]

    def __str__(self):
        return f'[{self.name}] {self.value}'


class DataCenter(models.Model):
    """数据中心"""
    id = models.BigAutoField(primary_key=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    remark = models.TextField(verbose_name=_('数据中心备注'), max_length=10000, blank=True, default='')

    # 指标数据服务
    metric_endpoint_url = models.CharField(
        verbose_name=_('指标监控系统查询接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    metric_receive_url = models.CharField(
        verbose_name=_('指标监控系统接收接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    metric_remark = models.CharField(verbose_name=_('指标监控系统备注'), max_length=255, blank=True, default='')

    # 日志服务
    loki_endpoint_url = models.CharField(
        verbose_name=_('日志聚合系统查询接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    loki_receive_url = models.CharField(
        verbose_name=_('日志聚合系统接收接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    loki_remark = models.CharField(verbose_name=_('日志聚合系统备注'), max_length=255, blank=True, default='')

    class Meta:
        db_table = 'screenvis_data_center'
        ordering = ['sort_weight']
        verbose_name = _('机构数据中心')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def clean(self):
        if self.metric_endpoint_url:
            try:
                URLValidator(self.metric_endpoint_url)
            except ValidationError:
                raise ValidationError(message={'metric_endpoint_url': gettext('不是一个有效的网址')})

        if self.loki_endpoint_url:
            try:
                URLValidator(self.loki_endpoint_url)
            except ValidationError:
                raise ValidationError(message={'loki_endpoint_url': gettext('不是一个有效的网址')})


class MetricMonitorUnit(models.Model):
    """
    监控单元
    """
    class UnitType(models.TextChoices):
        HOST = 'host', _('主机')
        CEPH = 'ceph', _('Ceph')
        TIDB = 'tidb', _('TiDB')

    id = models.BigAutoField(primary_key=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    name = models.CharField(verbose_name=_('名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    unit_type = models.CharField(verbose_name=_('类型'), max_length=16, choices=UnitType.choices)
    job_tag = models.CharField(
        verbose_name=_('标签名称'), max_length=255, default='', help_text=_('模板：xxx_xxx_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')
    data_center = models.ForeignKey(
        to=DataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)

    class Meta:
        db_table = 'screenvis_metric_unit'
        ordering = ['sort_weight']
        verbose_name = _('指标数据监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class LogMonitorUnit(models.Model):
    class LogType(models.TextChoices):
        HTTP = 'http', 'HTTP'
        NAT = 'nat', 'NAT'

    id = models.BigAutoField(primary_key=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    name = models.CharField(max_length=50, null=False, blank=False, verbose_name=_("日志单元名称"))
    name_en = models.CharField(verbose_name=_('日志单元英文名称'), max_length=128, default='')
    log_type = models.CharField(
        verbose_name=_("日志类型"), max_length=16, choices=LogType.choices, default=LogType.HTTP.value)
    job_tag = models.CharField(verbose_name=_('日志单元标识'), max_length=64, default='',
                               help_text=_('Loki日志中对应的job标识，模板xxx_log'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), help_text=_('值越小排序越靠前'), default=0)
    remark = models.CharField(max_length=255, blank=True, default="", verbose_name=_("备注"))
    data_center = models.ForeignKey(
        to=DataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)

    class Meta:
        db_table = "screenvis_log_unit"
        ordering = ['sort_weight']
        verbose_name = _("日志单元")
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class HostCpuUsage(UuidModel):
    """
    主机指标单元总cpu使用率时序数据
    """
    timestamp = models.PositiveBigIntegerField(null=False, blank=False, verbose_name="统计时间")
    unit = models.ForeignKey(
        to=MetricMonitorUnit, verbose_name='指标单元ID', on_delete=models.DO_NOTHING, null=True, blank=False,
        db_constraint=False, db_index=False)
    value = models.FloatField(verbose_name='CPU使用率', help_text='负数标识数据无效（查询失败的占位记录，便于后补）')

    class Meta:
        db_table = 'screenvis_hostcpuusage'
        ordering = ['-timestamp']
        verbose_name = _('主机指标单元总CPU使用率时序数据')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['timestamp'], name='idx_screen_cpuusage_ts')
        ]

    def __str__(self):
        return f'{self.id}({self.value}, {self.timestamp})'

    def clean(self):
        try:
            datetime.fromtimestamp(self.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            raise ValidationError({'timestamp': f'无效的时间戳，{str(exc)}，当前时间戳为:{int(dj_timezone.now().timestamp())}'})


class ApiAllowIP(models.Model):
    id = models.BigAutoField(primary_key=True)
    ip_value = models.CharField(
        verbose_name=_('IP'), max_length=100, help_text='192.168.1.1、 192.168.1.1/24、192.168.1.66 - 192.168.1.100')
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'screenvis_apiallowip'
        ordering = ['-creation_time']
        verbose_name = _('API允许访问的IP')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.id}({self.ip_value})'

    def clean(self):
        try:
            subnet = convert_iprange(self.ip_value)
        except Exception as exc:
            raise ValidationError({'ip_value': str(exc)})

        if isinstance(subnet, ipaddress.IPv4Network):
            self.ip_value = str(subnet)


class BaseService(models.Model):
    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('暂停服务')
        DELETED = 'deleted', _('删除')

    id = models.BigAutoField(primary_key=True)
    data_center = models.ForeignKey(
        to=DataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False, blank=True, default=None)
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    endpoint_url = models.CharField(
        max_length=255, verbose_name=_('服务地址url'), help_text='http(s)://{hostname}:{port}/')
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=255, verbose_name=_('密码'))
    status = models.CharField(
        verbose_name=_('服务状态'), max_length=32, choices=Status.choices, default=Status.ENABLE.value)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def clean(self):
        # 网址验证
        try:
            URLValidator(schemes=['http', 'https'])(self.endpoint_url)
        except ValidationError:
            raise ValidationError(message={'endpoint_url': gettext('不是一个有效的网址')})

    def raw_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.password = encryptor.encrypt(raw_password)


class ServerService(BaseService):
    class Meta:
        db_table = 'screenvis_serverservice'
        ordering = ['sort_weight']
        verbose_name = _('云主机服务单元')
        verbose_name_plural = verbose_name


class ObjectService(BaseService):
    class Meta:
        db_table = 'screenvis_objectservice'
        ordering = ['sort_weight']
        verbose_name = _('对象存储服务单元')
        verbose_name_plural = verbose_name


class BaseTimed(UuidModel):
    """
    时序数据基类
    """
    timestamp = models.PositiveBigIntegerField(null=False, blank=False, verbose_name="统计时间")

    class Meta:
        abstract = True

    def clean(self):
        try:
            datetime.fromtimestamp(self.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            raise ValidationError({'timestamp': f'无效的时间戳，{str(exc)}，当前时间戳为:{int(dj_timezone.now().timestamp())}'})


class ServerServiceTimedStats(BaseTimed):
    service = models.ForeignKey(
        to=ServerService, verbose_name='服务单元', on_delete=models.DO_NOTHING, null=True, blank=False,
        db_constraint=False, db_index=False)
    server_count = models.IntegerField(verbose_name=_('云主机数'), blank=True, default=0)
    disk_count = models.IntegerField(verbose_name=_('云硬盘数'), blank=True, default=0)
    ip_count = models.IntegerField(verbose_name=_('IP总数'), blank=True, default=0)
    ip_used_count = models.IntegerField(verbose_name=_('已用IP数'), blank=True, default=0)
    mem_size = models.IntegerField(verbose_name=_('内存总数(GiB)'), blank=True, default=0)
    mem_used_size = models.IntegerField(verbose_name=_('已用内存总数(GiB)'), blank=True, default=0)
    cpu_count = models.IntegerField(verbose_name=_('CPU总数'), blank=True, default=0)
    cpu_used_count = models.IntegerField(verbose_name=_('已用CPU总数'), blank=True, default=0)

    class Meta:
        db_table = 'screenvis_server_timedstats'
        ordering = ['-timestamp']
        verbose_name = _('云主机服务单元时序统计数据')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['timestamp'], name='idx_screen_server_tmstats_ts')
        ]


class VPNTimedStats(BaseTimed):
    service = models.ForeignKey(
        to=ServerService, verbose_name='服务单元', on_delete=models.DO_NOTHING, null=True, blank=False,
        db_constraint=False, db_index=False)
    vpn_online_count = models.IntegerField(verbose_name=_('VPN账户在线数'), blank=True, default=0)
    vpn_active_count = models.IntegerField(verbose_name=_('VPN有效数'), blank=True, default=0)
    vpn_count = models.IntegerField(verbose_name=_('VPN总数'), blank=True, default=0)

    class Meta:
        db_table = 'screenvis_vpn_timedstats'
        ordering = ['-timestamp']
        verbose_name = _('VPN时序统计数据')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['timestamp'], name='idx_screen_vpn_tmstats_ts')
        ]


class ObjectServiceTimedStats(BaseTimed):
    service = models.ForeignKey(
        to=ObjectService, verbose_name='服务单元', on_delete=models.DO_NOTHING, null=True, blank=False,
        db_constraint=False, db_index=False)
    bucket_count = models.IntegerField(verbose_name=_('存储桶总数'), blank=True, default=0)
    bucket_storage = models.BigIntegerField(verbose_name=_('存储桶总数据量'), blank=True, default=0)
    storage_used = models.BigIntegerField(verbose_name=_('已用容量'), blank=True, default=0)
    storage_capacity = models.BigIntegerField(verbose_name=_('总容量'), blank=True, default=0)

    class Meta:
        db_table = 'screenvis_object_timedstats'
        ordering = ['-timestamp']
        verbose_name = _('对象存储服务单元时序统计数据')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['timestamp'], name='idx_screen_obj_tmstats_ts')
        ]

# ObjectServiceTimedStats.objects.order_by('service_id', '-timestamp').distinct('service_id')
# ObjectServiceTimedStats.objects.values('service_id').annotate(last_timestamp=Max('timestamp')).values('service_id', 'last_timestamp')
