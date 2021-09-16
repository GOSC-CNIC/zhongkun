from django.db import models
from django.utils.translation import gettext_lazy as _

from service.models import ServiceConfig
from utils.model import UuidModel, get_encryptor


class MonitorProvider(UuidModel):
    name = models.CharField(verbose_name=_('监控服务名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控服务名称'), max_length=255, default='')
    endpoint_url = models.CharField(verbose_name=_('服务url地址'), max_length=255, default='',
                                    help_text=_('http(s)://example.cn/'))
    username = models.CharField(max_length=128, verbose_name=_('认证用户名'), blank=True, default='',
                                help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=255, verbose_name=_('认证密码'), blank=True, default='')
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

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
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='monitor_job_ceph_set', verbose_name=_('所属的服务'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

    class Meta:
        ordering = ['-creation']
        verbose_name = _('监控任务节点')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class MonitorJobServer(UuidModel):
    """
    主机集群监控工作节点
    """
    name = models.CharField(verbose_name=_('监控的主机集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的主机集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(verbose_name=_('主机集群标签名称'), max_length=255, default='')
    provider = models.ForeignKey(to=MonitorProvider, on_delete=models.CASCADE, related_name='+',
                                 verbose_name=_('监控服务配置'))
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='monitor_job_server_set', verbose_name=_('所属的服务'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

    class Meta:
        ordering = ['-creation']
        verbose_name = _('监控服务器节点')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
