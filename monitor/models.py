from django.db import models
from django.utils.translation import gettext_lazy as _

from service.models import ServiceConfig
from utils.model import UuidModel, get_encryptor
from users.models import UserProfile


class MonitorProvider(UuidModel):
    name = models.CharField(verbose_name=_('监控服务名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控服务名称'), max_length=255, default='')
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
        verbose_name = _('监控服务配置信息')
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
        db_constraint=False, verbose_name=_('管理用户'))
    sort_weight = models.IntegerField(verbose_name=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-sort_weight']
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

        return self.users.filter(id=user.id).exists()


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
        db_constraint=False, verbose_name=_('管理用户'))
    sort_weight = models.IntegerField(verbose_name=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-sort_weight']
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

        return self.users.filter(id=user.id).exists()


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
