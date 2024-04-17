from django.db import models
from django.utils.translation import gettext_lazy as _


# Create your models here.


class ProbeMonitorWebsite(models.Model):
    id = models.AutoField(primary_key=True, verbose_name=_('ID'))
    url_hash = models.CharField(verbose_name=_('网址hash值'), max_length=64, default='')
    is_tamper_resistant = models.BooleanField(verbose_name=_('防篡改'), default=False)
    uri = models.CharField(verbose_name=_('URI'), max_length=1024, default='', help_text='/a/b?query=123#test')
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    tls_time = models.FloatField(verbose_name=_('tls 时间'), default=0, help_text='')
    connect_time = models.FloatField(verbose_name=_('TCP 建立持续时间'), default=0, help_text='')
    processing_time = models.FloatField(verbose_name=_('连接成功到收到内容时间'), default=0, help_text='')
    resolve_time = models.FloatField(verbose_name=_('DNS 解析时间'), default=0, help_text='')
    transfer_time = models.FloatField(verbose_name=_('响应内容时间'), default=0, help_text='')
    status = models.CharField(verbose_name=_('状态'), max_length=3, default='', null=True, blank=True)



    class Meta:
        db_table = 'app_probe_monitor_website'
        ordering = ['-creation']
        verbose_name = _('探针任务')
        verbose_name_plural = verbose_name


class ProbeDetails(models.Model):
    CHKJW = 1
    BJLT = 2
    BJDX = 3

    TYPE = [
        (CHKJW, _("中国科技网")),
        (BJLT, _("北京联通")),
        (BJDX, _("北京电信")),
    ]

    INSTANCE_ID = 1
    id = models.AutoField(primary_key=True, verbose_name=_('ID'), default=INSTANCE_ID)
    probe_type = models.PositiveSmallIntegerField(verbose_name=_('探针'), choices=TYPE, default=None)
    version = models.IntegerField(verbose_name=_('版本号'), default=0, blank=True)

    class Meta:
        db_table = 'app_probe_details'
        verbose_name = _('探针信息')
        verbose_name_plural = verbose_name

    @classmethod
    def get_instance(cls):

        inst = cls.objects.filter(id=cls.INSTANCE_ID).first()
        if not inst:
            return None

        return inst
