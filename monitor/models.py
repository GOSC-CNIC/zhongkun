import hashlib

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from service.models import DataCenter, ServiceConfig
from service.managers import ServiceManager
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
    job_tag = models.CharField(verbose_name=_('CEPH集群标签名称'), max_length=255, default='')
    provider = models.ForeignKey(to=MonitorProvider, on_delete=models.CASCADE, related_name='+',
                                 verbose_name=_('监控服务配置'))
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
    organization = models.ForeignKey(
        verbose_name=_('监控机构'), to=DataCenter, related_name='+', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None
    )
    service = models.ForeignKey(
        to=ServiceConfig, verbose_name='云主机服务单元', on_delete=models.SET_NULL, null=True, default=None, blank=True,
        related_name='+', db_constraint=False, db_index=False,
    )

    class Meta:
        ordering = ['sort_weight']
        verbose_name = _('Ceph监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def user_has_perm(self, user):
        """
        用户是否有访问此服务的管理权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user or not user.id:
            return False

        if self.users.filter(id=user.id).exists():
            return True

        if self.service_id:
            s = ServiceManager.get_service_if_admin(user=user, service_id=self.service_id)
            if s is not None:
                return True

        return False


class MonitorJobServer(UuidModel):
    """
    主机集群监控单元
    """
    name = models.CharField(verbose_name=_('监控的主机集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的主机集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(verbose_name=_('主机集群标签名称'), max_length=255, default='')
    provider = models.ForeignKey(to=MonitorProvider, on_delete=models.CASCADE, related_name='+',
                                 verbose_name=_('监控服务配置'))
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
    organization = models.ForeignKey(
        verbose_name=_('监控机构'), to=DataCenter, related_name='+', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None
    )
    service = models.ForeignKey(
        to=ServiceConfig, verbose_name='云主机服务单元', on_delete=models.SET_NULL, null=True, default=None, blank=True,
        related_name='+', db_constraint=False, db_index=False,
    )

    class Meta:
        ordering = ['sort_weight']
        verbose_name = _('服务器监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def user_has_perm(self, user):
        """
        用户是否有访问此服务的管理权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user or not user.id:
            return False

        if self.users.filter(id=user.id).exists():
            return True

        if self.service_id:
            s = ServiceManager.get_service_if_admin(user=user, service_id=self.service_id)
            if s is not None:
                return True

        return False


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
        ordering = ['-creation']
        verbose_name = _('科技云会视频会议监控工作节点')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorWebsite(UuidModel):
    """
    网站监控
    """
    name = models.CharField(verbose_name=_('网站名称'), max_length=255, default='')
    url = models.URLField(verbose_name=_('要监控的网址'), max_length=2048, default='', help_text='http(s)://xxx.xxx')
    url_hash = models.CharField(verbose_name=_('网址hash值'), max_length=64, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'))
    modification = models.DateTimeField(verbose_name=_('修改时间'))
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, related_name='+',
        on_delete=models.SET_NULL, blank=True, null=True, db_constraint=False)
    is_attention = models.BooleanField(verbose_name=_('特别关注'), default=False)
    is_tamper_resistant = models.BooleanField(verbose_name=_('防篡改'), default=False)
    scheme = models.CharField(verbose_name=_('协议'), max_length=32, default='', help_text='https|ftps://')
    hostname = models.CharField(verbose_name=_('域名'), max_length=255, default='', help_text='hostname:8000')
    uri = models.CharField(verbose_name=_('URI'), max_length=1024, default='', help_text='/a/b?query=123#test')

    class Meta:
        db_table = 'monitor_website'
        ordering = ['-creation']
        verbose_name = _('网站监控')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        url_hash = get_str_hash(self.full_url)
        if url_hash != self.url_hash:
            self.url_hash = url_hash
            if update_fields and 'url_hash' not in update_fields:
                update_fields.append('url_hash')

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @property
    def full_url(self):
        return self.scheme + self.hostname + self.uri


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
    job_tag = models.CharField(verbose_name=_('TiDB集群标签名称'), max_length=255, default='')
    provider = models.ForeignKey(to=MonitorProvider, on_delete=models.CASCADE, related_name='+',
                                 verbose_name=_('监控服务配置'))
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
    organization = models.ForeignKey(
        verbose_name=_('监控机构'), to=DataCenter, related_name='+', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None
    )
    version = models.CharField(verbose_name=_('TiDB版本'), max_length=32, blank=True, default='', help_text='xx.xx.xx')
    service = models.ForeignKey(
        to=ServiceConfig, verbose_name='云主机服务单元', on_delete=models.SET_NULL, null=True, default=None, blank=True,
        related_name='+', db_constraint=False, db_index=False,
    )

    class Meta:
        db_table = 'monitor_unit_tidb'
        ordering = ['sort_weight']
        verbose_name = _('TiDB监控单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def user_has_perm(self, user):
        """
        用户是否有访问此服务的管理权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user or not user.id:
            return False

        if self.users.filter(id=user.id).exists():
            return True

        if self.service_id:
            s = ServiceManager.get_service_if_admin(user=user, service_id=self.service_id)
            if s is not None:
                return True

        return False

    @classmethod
    def get_user_unit_queryset(cls, user_id: str):
        return cls.objects.filter(users__id=user_id).all()


class LogSiteType(UuidModel):
    """
    日志网站类别
    """
    name = models.CharField(
        max_length=64, unique=True, null=False, blank=False, verbose_name="日志网站类别名称", help_text=_('对象存储、一体云'))
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=128, default='')
    sort_weight = models.IntegerField(verbose_name='排序值', help_text='值越小排序越靠前')
    desc = models.CharField(max_length=255, blank=True, default='', verbose_name="备注")
    creation = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modification = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "log_site_type"
        ordering = ['sort_weight']
        verbose_name = "日志网站类别"
        verbose_name_plural = verbose_name


class LogSite(UuidModel):
    class LogType(models.TextChoices):
        HTTP = 'http', 'HTTP'
        NAT = 'nat', 'NAT'

    name = models.CharField(max_length=50, null=False, blank=False, verbose_name="日志单元站点名称")
    name_en = models.CharField(verbose_name=_('日志单元英文名称'), max_length=128, default='')
    log_type = models.CharField(
        verbose_name="日志类型", max_length=16, choices=LogType.choices, default=LogType.HTTP.value)
    site_type = models.ForeignKey(
        to=LogSiteType, db_constraint=False, on_delete=models.SET_NULL, null=True,
        related_name='+', verbose_name="站点类别")
    job_tag = models.CharField(verbose_name=_('网站日志单元标识'), max_length=64, default='',
                               help_text=_('Loki日志中对应的job标识'))
    provider = models.ForeignKey(
        to=MonitorProvider, db_constraint=False, on_delete=models.CASCADE,
        related_name='+', verbose_name=_('日志数据查询服务提供者'))
    sort_weight = models.IntegerField(verbose_name='排序值', help_text='值越小排序越靠前')
    desc = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")
    organization = models.ForeignKey(
        verbose_name=_('机构'), to=DataCenter, related_name='+', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None
    )
    creation = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modification = models.DateTimeField(verbose_name='修改时间', auto_now=True)
    users = models.ManyToManyField(
        to=UserProfile, db_table='log_site_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)

    class Meta:
        db_table = "log_site"
        ordering = ['sort_weight']
        verbose_name = "日志单元站点"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def user_has_perm(self, user):
        """
        用户是否有访问此服务的管理权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user or not user.id:
            return False

        if self.users.filter(id=user.id).exists():
            return True

        return False
