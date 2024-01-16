import hashlib
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone

from service.models import OrgDataCenter
from utils.model import UuidModel, get_encryptor
from users.models import UserProfile


def get_str_hash(s: str):
    """
    计算字符串的hash1
    """
    return hashlib.sha1(s.encode(encoding='utf-8')).hexdigest()


class MonitorProvider(UuidModel):
    name = models.CharField(verbose_name=_('监控服务名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控服务英文名称'), max_length=255, default='')
    endpoint_url = models.CharField(verbose_name=_('查询接口'), max_length=255, default='',
                                    help_text=_('http(s)://example.cn/'))
    username = models.CharField(max_length=128, verbose_name=_('认证用户名'), blank=True, default='',
                                help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=255, verbose_name=_('认证密码'), blank=True, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    receive_url = models.CharField(
        verbose_name=_('接收接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    bucket_service_name = models.CharField(
        max_length=128, verbose_name=_('存储桶所在对象存储服务名称'), blank=True, default='')
    bucket_service_url = models.CharField(
        verbose_name=_('存储桶所在对象存储服务地址'), max_length=255, blank=True, default='',
        help_text=_('http(s)://example.cn/'))
    bucket_name = models.CharField(max_length=128, verbose_name=_('存储桶名称'), blank=True, default='')
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')

    class Meta:
        ordering = ['-creation']
        verbose_name = _('监控数据查询提供者服务')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

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


class MonitorJobCeph(UuidModel):
    """
    ceph集群监控工作节点
    """
    name = models.CharField(verbose_name=_('监控的CEPH集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的CEPH集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(
        verbose_name=_('CEPH集群标签名称'), max_length=255, default='', help_text=_('模板：xxx_ceph_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    users = models.ManyToManyField(
        to=UserProfile, db_table='monitor_ceph_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')
    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)

    class Meta:
        db_table = 'monitor_monitorjobceph'
        ordering = ['sort_weight']
        verbose_name = _('Ceph监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorJobServer(UuidModel):
    """
    主机集群监控单元
    """
    name = models.CharField(verbose_name=_('监控的主机集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的主机集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(
        verbose_name=_('主机集群标签名称'), max_length=255, default='', help_text=_('模板：xxx_node_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    users = models.ManyToManyField(
        to=UserProfile, db_table='monitor_server_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')
    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)

    class Meta:
        db_table = 'monitor_monitorjobserver'
        ordering = ['sort_weight']
        verbose_name = _('服务器监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorJobVideoMeeting(UuidModel):
    """
    科技云会视频会议监控工作节点
    """
    name = models.CharField(verbose_name=_('科技云会服务节点院所名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('科技云会服务节点院所英文名称'), max_length=255, default='')
    job_tag = models.CharField(verbose_name=_('标签名称'), max_length=255, default='')
    ips = models.CharField(verbose_name=_('ipv4地址'), max_length=255, default='', help_text=_('多个ip用“;”分割'))
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    provider = models.ForeignKey(to=MonitorProvider, on_delete=models.CASCADE, related_name='+',
                                 verbose_name=_('监控服务配置'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.CharField(verbose_name=_('备注'), max_length=1024, blank=True, default='')

    class Meta:
        db_table = 'monitor_monitorjobvideomeeting'
        ordering = ['-creation']
        verbose_name = _('科技云会视频会议监控工作节点')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorWebsiteBase(UuidModel):
    """
    网站监控基类
    """
    name = models.CharField(verbose_name=_('网站名称'), max_length=255, default='')
    url_hash = models.CharField(verbose_name=_('网址hash值'), max_length=64, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'))
    modification = models.DateTimeField(verbose_name=_('修改时间'))
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    is_tamper_resistant = models.BooleanField(verbose_name=_('防篡改'), default=False)
    scheme = models.CharField(verbose_name=_('协议'), max_length=32, default='', help_text='https|tcp://')
    hostname = models.CharField(verbose_name=_('域名[:端口]'), max_length=255, default='', help_text='hostname:8000')
    uri = models.CharField(verbose_name=_('URI'), max_length=1024, default='', help_text='/a/b?query=123#test')

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    @property
    def full_url(self):
        return self.scheme + self.hostname + self.uri


class MonitorWebsite(MonitorWebsiteBase):
    """
    网站监控
        * 可同时关联“user”和"数据中心(odc)"，或者关联其一，原则上不应该存在同时关联和都未关联的情况
        * 关联用户有权限管理监控任务和访问监控数据
        * 关联odc,odc管理员有权限访问监控数据，但是无权限管理监控任务
        * 只关联odc的任务，是自动为数据中心关联的各服务单元（云主机、对象存储、日志和指标监控）创建的监控任务
        * 计量扣费，如果关联了用户，向关联用户扣费，未关联用户不扣费
    """
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, related_name='+',
        on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False,
        help_text=_('关联用户有权限管理监控任务和查询监控数据；用户与数据中心原则上只能关联其一'))
    odc = models.ForeignKey(
        verbose_name=_('数据中心'), to=OrgDataCenter, related_name='+',
        on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False, default=None,
        help_text=_('关联数据中心后，数据中心管理员有权限访问此监控任务的数据，无监控任务的管理权限；数据中心与用户原则上只能关联其一'))
    is_attention = models.BooleanField(verbose_name=_('特别关注'), default=False)

    class Meta:
        db_table = 'monitor_website'
        ordering = ['-creation']
        verbose_name = _('网站监控')
        verbose_name_plural = verbose_name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        url_hash = get_str_hash(self.full_url)
        if url_hash != self.url_hash:
            self.url_hash = url_hash
            if update_fields and 'url_hash' not in update_fields:
                update_fields.append('url_hash')

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def calculate_url_hash(self):
        return get_str_hash(self.full_url)

    def clean(self):
        if self.scheme == 'tcp://':
            hostname_list = self.hostname.split(':')
            try:
                part = int(hostname_list[1])
                if part not in range(0, 65536):
                    raise ValidationError({'hostname': _('端口范围 0-65535 。')})
            except ValidationError as exc:
                raise exc
            except Exception as e:
                raise ValidationError({'hostname': _('hostname 格式错误,tcp 协议 hostname 格式为: "地址:端口"。')})

            if self.uri != '/':
                raise ValidationError({'uri': _('uri 格式错误,tcp 协议 uri 只能为 "/"。')})

            if self.is_tamper_resistant:
                raise ValidationError({'is_tamper_resistant': _('tcp监控任务不支持防篡改监控')})


class MonitorWebsiteRecord(MonitorWebsiteBase):
    """
    网站监控记录
    """
    class RecordType(models.TextChoices):
        DELETED = 'deleted', _('删除')

    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    record_time = models.DateTimeField(verbose_name=_('记录时间'))
    type = models.CharField(verbose_name=_('记录类型'), max_length=16, choices=RecordType.choices,)

    class Meta:
        db_table = 'monitor_website_record'
        ordering = ['-record_time']
        verbose_name = _('网站监控任务记录')
        verbose_name_plural = verbose_name

    @classmethod
    def create_record_for_website(cls, site: MonitorWebsite):
        if not site.user_id:
            return None

        record = cls(
            id=site.id,
            name=site.name,
            url_hash=site.url_hash,
            creation=site.creation,
            modification=site.modification,
            remark=site.remark,
            is_tamper_resistant=site.is_tamper_resistant,
            scheme=site.scheme,
            hostname=site.hostname,
            uri=site.uri,
            user_id=site.user_id,
            username=site.user.username,
            record_time=timezone.now(),
            type=cls.RecordType.DELETED.value
        )
        record.save(force_insert=True)
        return record


class MonitorWebsiteTask(UuidModel):
    """
    网站监控任务
    """
    url = models.CharField(verbose_name=_('要监控的网址'), max_length=2048, default='')
    url_hash = models.CharField(verbose_name=_('网址hash值'), unique=True, max_length=64, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    is_tamper_resistant = models.BooleanField(verbose_name=_('防篡改'), default=False)

    class Meta:
        db_table = 'monitor_website_task'
        ordering = ['-creation']
        verbose_name = _('网站监控任务')
        verbose_name_plural = verbose_name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.url_hash = get_str_hash(self.url)
        if isinstance(update_fields, list) and 'url' in update_fields:
            update_fields.append('url_hash')

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class MonitorWebsiteVersion(models.Model):
    """
    网站监控任务变动最新版本
    """
    INSTANCE_ID = 1

    id = models.IntegerField(primary_key=True, default=INSTANCE_ID)
    version = models.BigIntegerField(
        verbose_name=_('监控任务版本号'), default=1, help_text=_('用于区分网站监控任务表是否有变化'))
    creation = models.DateTimeField(verbose_name=_('创建时间'))
    modification = models.DateTimeField(verbose_name=_('修改时间'))
    pay_app_service_id = models.CharField(
        verbose_name=_('余额结算APP子服务ID'), max_length=36, default='',
        help_text=_('此服务对应的APP服务（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费'))

    class Meta:
        db_table = 'monitor_website_version_provider'
        ordering = ['-creation']
        verbose_name = _('网站监控任务版本')
        verbose_name_plural = verbose_name

    @classmethod
    def get_instance(cls, select_for_update: bool = False):
        if select_for_update:
            inst = cls.objects.select_for_update().filter(id=cls.INSTANCE_ID).first()
        else:
            inst = cls.objects.filter(id=cls.INSTANCE_ID).first()

        if inst is not None:
            return inst

        nt = timezone.now()
        inst = cls(id=cls.INSTANCE_ID, version=0, creation=nt, modification=nt)
        inst.save(force_insert=True)
        if select_for_update:
            inst = cls.objects.select_for_update().filter(id=cls.INSTANCE_ID).first()

        return inst

    def version_add_1(self):
        self.version += 1
        self.modification = timezone.now()
        self.save(update_fields=['version', 'modification'])


class WebsiteDetectionPoint(UuidModel):
    name = models.CharField(verbose_name=_('监控探测点名称'), max_length=128, default='')
    name_en = models.CharField(verbose_name=_('监控探测点英文名称'), max_length=128, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'))
    modification = models.DateTimeField(verbose_name=_('修改时间'))
    provider = models.ForeignKey(
        to=MonitorProvider, verbose_name=_('监控查询服务配置信息'), on_delete=models.SET_NULL,
        related_name='+', db_constraint=False, null=True, default=None)
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    enable = models.BooleanField(verbose_name=_('是否启用'), default=True)

    class Meta:
        db_table = 'website_detection_point'
        ordering = ['-creation']
        verbose_name = _('网站监控探测点')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorJobTiDB(UuidModel):
    """
    TiDB集群监控工作节点
    """
    name = models.CharField(verbose_name=_('监控的TiDB集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的TiDB集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(
        verbose_name=_('TiDB集群标签名称'), max_length=255, default='', help_text=_('模板：xxx_tidb_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    users = models.ManyToManyField(
        to=UserProfile, db_table='monitor_tidb_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')
    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)
    version = models.CharField(verbose_name=_('TiDB版本'), max_length=32, blank=True, default='', help_text='xx.xx.xx')

    class Meta:
        db_table = 'monitor_unit_tidb'
        ordering = ['sort_weight']
        verbose_name = _('TiDB监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    @classmethod
    def get_user_unit_queryset(cls, user_id: str):
        return cls.objects.filter(users__id=user_id).all()


class LogSiteType(UuidModel):
    """
    日志网站类别
    """
    name = models.CharField(
        max_length=64, unique=True, null=False, blank=False,
        verbose_name=_("日志网站类别名称"), help_text=_('对象存储、一体云'))
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=128, default='')
    sort_weight = models.IntegerField(verbose_name=_('排序值'), help_text=_('值越小排序越靠前'))
    desc = models.CharField(max_length=255, blank=True, default='', verbose_name=_("备注"))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "log_site_type"
        ordering = ['sort_weight']
        verbose_name = "日志单元类别"
        verbose_name_plural = verbose_name


class LogSite(UuidModel):
    class LogType(models.TextChoices):
        HTTP = 'http', 'HTTP'
        NAT = 'nat', 'NAT'

    name = models.CharField(max_length=50, null=False, blank=False, verbose_name=_("日志单元站点名称"))
    name_en = models.CharField(verbose_name=_('日志单元英文名称'), max_length=128, default='')
    log_type = models.CharField(
        verbose_name=_("日志类型"), max_length=16, choices=LogType.choices, default=LogType.HTTP.value)
    site_type = models.ForeignKey(
        to=LogSiteType, db_constraint=False, on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name=_("站点类别"))
    job_tag = models.CharField(verbose_name=_('网站日志单元标识'), max_length=64, default='',
                               help_text=_('Loki日志中对应的job标识，模板xxx_log'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), help_text=_('值越小排序越靠前'))
    desc = models.CharField(max_length=255, blank=True, default="", verbose_name=_("备注"))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)
    users = models.ManyToManyField(
        to=UserProfile, db_table='log_site_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)

    class Meta:
        db_table = "log_site"
        ordering = ['sort_weight']
        verbose_name = _("日志单元")
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class LogSiteTimeReqNum(UuidModel):
    """日志站点每分钟访问量"""
    timestamp = models.PositiveBigIntegerField(null=False, blank=False, verbose_name="统计时间")
    site = models.ForeignKey(
        verbose_name='日志站点', to=LogSite, on_delete=models.DO_NOTHING, null=True, blank=False,
        db_constraint=False, db_index=False)
    count = models.IntegerField(verbose_name='请求量', help_text='负数标识数据无效（查询失败的占位记录，便于后补）')

    class Meta:
        db_table = 'log_site_time_req_num'
        ordering = ['-timestamp']
        verbose_name = "日志单元时序请求量"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['timestamp'], name='idx_timestamp')
        ]

    def __str__(self):
        return f'{self.id}({self.count}, {self.timestamp})'

    def clean(self):
        try:
            datetime.fromtimestamp(self.timestamp, tz=timezone.get_default_timezone())
        except Exception as exc:
            raise ValidationError({'timestamp': f'无效的时间戳，{str(exc)}，当前时间戳为:{int(timezone.now().timestamp())}'})


class TotalReqNum(UuidModel):
    """
    服务总请求数记录, 包括一体云后端和对象存储
    """
    singleton_instance_id = 1

    req_num = models.IntegerField(verbose_name=_('服务总请求数'), default=0)
    until_time = models.DateTimeField(verbose_name=_('截止到时间'))
    creation = models.DateTimeField(verbose_name=_('创建时间'))
    modification = models.DateTimeField(verbose_name=_('更新时间'))

    class Meta:
        db_table = 'total_req_num'
        ordering = ['creation']
        verbose_name = _("本服务和对象存储总请求数")
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        self.id = self.singleton_instance_id
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj = cls.objects.filter(id=cls.singleton_instance_id).first()
        if obj:
            return obj

        nt = timezone.now()
        until_time = nt.replace(hour=0, minute=0, second=0, microsecond=0)
        obj = cls(req_num=0, until_time=until_time, creation=nt, modification=nt)
        obj.save(force_insert=True)
        return obj


class ErrorLog(UuidModel):
    status_code = models.IntegerField(verbose_name=_('状态码'), blank=True, default=0)
    method = models.CharField(verbose_name=_('请求方法'), max_length=32, blank=True, default='')
    full_path = models.CharField(verbose_name=_("URI"), max_length=1024, blank=True, default='')
    message = models.TextField(verbose_name=_("日志信息"), blank=True, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    username = models.CharField(verbose_name=_("请求用户"), max_length=128, blank=True, default='')

    class Meta:
        db_table = 'error_log'
        ordering = ['-creation']
        verbose_name = _("错误日志")
        verbose_name_plural = verbose_name

    def clean(self):
        if not (0 <= self.status_code < 600):
            raise ValidationError(message={'status_code': gettext('状态码必须在0-600之间')})
