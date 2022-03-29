from decimal import Decimal

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from utils.model import UuidModel, OwnerType, PayType
from users.models import UserProfile
from vo.models import VirtualOrganization
from servers.models import Server
from service.models import ServiceConfig
from storage.models import ObjectsService
from bill.models import PaymentHistory


class PaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', _('待支付')
    PAID = 'paid', _('已支付')
    CANCELLED = 'cancelled', _('作废')


class MeteringServer(UuidModel):
    """
    服务器云主机计量
    """
    OwnerType = OwnerType

    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+',
                                on_delete=models.DO_NOTHING, db_index=False)
    server_id = models.CharField(verbose_name=_('云服务器ID'), max_length=36)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    cpu_hours = models.FloatField(
        verbose_name=_('CPU Hour'), blank=True, default=0, help_text=_('云服务器的CPU Hour数'))
    ram_hours = models.FloatField(
        verbose_name=_('内存GiB Hour'), blank=True, default=0, help_text=_('云服务器的内存Gib Hour数'))
    disk_hours = models.FloatField(
        verbose_name=_('系统盘GiB Hour'), blank=True, default=0, help_text=_('云服务器的系统盘Gib Hour数'))
    public_ip_hours = models.FloatField(
        verbose_name=_('IP Hour'), blank=True, default=0, help_text=_('云服务器的公网IP Hour数'))
    snapshot_hours = models.FloatField(
        verbose_name=_('快照GiB Hour'), blank=True, default=0, help_text=_('云服务器的快照小时数'))
    upstream = models.FloatField(
        verbose_name=_('上行流量GiB'), blank=True, default=0, help_text=_('云服务器的上行流量Gib'))
    downstream = models.FloatField(
        verbose_name=_('下行流量GiB'), blank=True, default=0, help_text=_('云服务器的下行流量Gib'))
    pay_type = models.CharField(verbose_name=_('云服务器付费方式'), max_length=16, choices=Server.PayType.choices)
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    trade_amount = models.DecimalField(verbose_name=_('交易金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    payment_status = models.CharField(
        verbose_name=_('支付状态'), max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_history = models.OneToOneField(
        verbose_name=_('支付记录'), to=PaymentHistory, related_name='+',
        null=True, on_delete=models.SET_NULL, default=None)

    class Meta:
        verbose_name = _('云服务器资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_server'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(fields=['date', 'server_id'], name='unique_date_server')
        ]

    def __repr__(self):
        return gettext('云服务器资源计量') + f'[server id {self.server_id}]'


class MeteringDisk(UuidModel):
    """
    云硬盘计量
    """
    OwnerType = OwnerType

    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+',
                                on_delete=models.DO_NOTHING, db_index=False)
    disk_id = models.CharField(verbose_name=_('云硬盘ID'), max_length=36)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    size_hours = models.FloatField(
        verbose_name=_('云硬盘GiB Hour'), blank=True, default=0, help_text=_('云硬盘Gib Hour数'))
    snapshot_hours = models.FloatField(
        verbose_name=_('快照GiB Hour'), blank=True, default=0, help_text=_('云硬盘快照GiB小时数'))
    pay_type = models.CharField(verbose_name=_('云硬盘付费方式'), max_length=16, choices=PayType.choices)
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    trade_amount = models.DecimalField(verbose_name=_('交易金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    payment_status = models.CharField(
        verbose_name=_('支付状态'), max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_history = models.OneToOneField(
        verbose_name=_('支付记录'), to=PaymentHistory, related_name='+',
        null=True, on_delete=models.SET_NULL, default=None)

    class Meta:
        verbose_name = _('云硬盘资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_disk'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(fields=['date', 'disk_id'], name='unique_date_disk')
        ]

    def __repr__(self):
        return gettext('云硬盘资源计量') + f'[disk id {self.disk_id}]'


class MeteringObjectStorage(UuidModel):
    """
    对象存储计量
    """
    service = models.ForeignKey(to=ObjectsService, verbose_name=_('服务'), related_name='+',
                                on_delete=models.DO_NOTHING, db_index=False)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True)
    bucket_id = models.CharField(verbose_name=_('存储桶ID'), max_length=36)
    bucket_name = models.CharField(verbose_name=_('存储桶名称'), max_length=63)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    storage = models.FloatField(
        verbose_name=_('存储容量GiB'), blank=True, default=0, help_text=_('存储桶的存储容量GiB'))
    downstream = models.FloatField(
        verbose_name=_('下行流量GiB'), blank=True, default=0, help_text=_('存储桶的下行流量GiB'))
    replication = models.FloatField(
        verbose_name=_('同步流量GiB'), blank=True, default=0, help_text=_('存储桶的同步流量GiB'))
    get_request = models.IntegerField(verbose_name=_('get请求次数'), default=0, help_text=_('存储桶的get请求次数'))
    put_request = models.IntegerField(verbose_name=_('put请求次数'), default=0, help_text=_('存储桶的put请求次数'))
    pay_type = models.CharField(verbose_name=_('对象存储付费方式'), max_length=16, choices=Server.PayType.choices)
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    trade_amount = models.DecimalField(verbose_name=_('交易金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    payment_status = models.CharField(
        verbose_name=_('支付状态'), max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    payment_history = models.OneToOneField(
        verbose_name=_('支付记录'), to=PaymentHistory, related_name='+',
        null=True, on_delete=models.SET_NULL, default=None)

    class Meta:
        verbose_name = _('对象存储资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_object_storage'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['date', 'service_id', 'user_id', 'bucket_name'], name='unique_date_bucket'
            )
        ]
