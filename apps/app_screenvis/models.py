from datetime import datetime

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone as dj_timezone
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

from utils.model import UuidModel


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
