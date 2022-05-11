import random
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator

from utils.model import UuidModel, OwnerType, PayType


def generate_order_sn():
    """
    生成订单编号
    长22位: 日期+纳秒+2位随机数
    """
    t = timezone.now()
    rand = random.randint(0, 99)
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}{t.microsecond:06}{rand:02}"


class ResourceType(models.TextChoices):
    VM = 'vm', _('云主机')
    DISK = 'disk', _('云硬盘')
    BUCKET = 'bucket', _('存储桶')


class Order(models.Model):
    OwnerType = OwnerType

    class OrderType(models.TextChoices):
        NEW = 'new', _('新购')
        RENEWAL = 'renewal', _('续费')
        UPGRADE = 'upgrade', _('升级')
        DOWNGRADE = 'downgrade', _('降级')

    class Status(models.TextChoices):
        PAID = 'paid', _('已支付')
        UNPAID = 'unpaid', _('未支付')
        CANCELLED = 'cancelled', _('作废')
        REFUND = 'refund', _('退款')

    class PaymentMethod(models.TextChoices):
        UNKNOWN = 'unknown', _('未知')
        BALANCE = 'balance', _('余额')
        VOUCHER = 'voucher', _('代金卷')

    class TradingStatus(models.TextChoices):
        OPENING = 'opening', _('交易中')
        UNDELIVERED= 'undelivered', _('订单资源交付失败')
        COMPLETED = 'completed', _('交易成功')
        CLOSED = 'closed', _('交易关闭')

    id = models.CharField(verbose_name=_('订单编号'), max_length=32, primary_key=True, editable=False)
    order_type = models.CharField(
        verbose_name=_('订单类型'), max_length=16, choices=OrderType.choices, default=OrderType.NEW)
    status = models.CharField(
        verbose_name=_('订单状态'), max_length=16, choices=Status.choices, default=Status.PAID)
    total_amount = models.DecimalField(verbose_name=_('总金额'), max_digits=10, decimal_places=2, default=0.0)
    pay_amount = models.DecimalField(verbose_name=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)

    service_id = models.CharField(verbose_name=_('服务id'), max_length=36, blank=True, default='')
    service_name = models.CharField(verbose_name=_('服务名称'), max_length=255, blank=True, default='')
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices, default=ResourceType.VM)
    instance_config = models.JSONField(verbose_name=_('资源的规格和配置'), null=False, blank=True, default=dict)
    period = models.IntegerField(verbose_name=_('订购时长(月)'), blank=True, default=0)

    payment_time = models.DateTimeField(verbose_name=_('支付时间'), null=True, blank=True, default=None)
    pay_type = models.CharField(verbose_name=_('结算方式'), max_length=16, choices=PayType.choices)
    payment_method = models.CharField(
        verbose_name=_('付款方式'), max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.UNKNOWN)

    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    start_time = models.DateTimeField(verbose_name=_('起用时间'), null=True, blank=True, default=None)
    end_time = models.DateTimeField(verbose_name=_('终止时间'), null=True, blank=True, default=None)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=64, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=256, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)

    completion_time = models.DateTimeField(verbose_name=_('交易完成时间'), null=True, blank=True, default=None)
    trading_status = models.CharField(
        verbose_name=_('交易状态'), max_length=16, choices=TradingStatus.choices, default=TradingStatus.OPENING.value)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)

    class Meta:
        verbose_name = _('订单')
        verbose_name_plural = verbose_name
        db_table = 'order'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'order[{self.id}]'

    @staticmethod
    def generate_order_sn():
        return generate_order_sn()

    def enforce_order_id(self):
        if not self.id:
            self.id = self.generate_order_sn()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.enforce_order_id()
        return super().save(force_insert=force_insert, force_update=force_update,
                            using=using, update_fields=update_fields)

    def set_paid(self, pay_amount: Decimal = None, payment_method: str = None):
        if not payment_method:
            payment_method = self.PaymentMethod.BALANCE.value
        elif payment_method not in self.PaymentMethod.values:
            raise ValueError(_('无效的付款方式'))

        self.pay_amount = self.total_amount if pay_amount is None else pay_amount
        self.status = self.Status.PAID.value
        self.payment_method = payment_method
        self.payment_time = timezone.now()
        self.save(update_fields=['pay_amount', 'status', 'payment_method', 'payment_time'])

    def set_cancel(self):
        self.status = self.Status.CANCELLED.value
        self.trading_status = self.TradingStatus.CLOSED.value
        self.save(update_fields=['status', 'trading_status'])


class Resource(UuidModel):
    class InstanceStatus(models.TextChoices):
        WAIT = 'wait', _('待交付')
        SUCCESS = 'success', _('交付成功')
        FAILED = 'failed', _('交付失败')

    order = models.ForeignKey(
        to=Order, on_delete=models.SET_NULL, related_name='resource_set', null=True, verbose_name=_('订单'))
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices)
    instance_id = models.CharField(verbose_name=_('资源实例id'), max_length=36, blank=True, default='')
    instance_status = models.CharField(
        verbose_name=_('资源交付结果'), max_length=16, choices=InstanceStatus.choices, default=InstanceStatus.WAIT)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    instance_remark = models.CharField(verbose_name=_('资源实例备注'), max_length=255, blank=True, default='')
    desc = models.CharField(verbose_name=_('资源交付结果描述'), max_length=255, blank=True, default='')
    last_deliver_time = models.DateTimeField(
        verbose_name=_('上次交付创建资源时间'), null=True, blank=True, default=None,
        help_text=_('用于记录上次交付资源的时间，防止并发重复交付')
    )

    class Meta:
        verbose_name = _('订单资源')
        verbose_name_plural = verbose_name
        db_table = 'order_resource'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'Resource([{self.resource_type}]{self.instance_id})'


class Price(UuidModel):
    vm_ram = models.DecimalField(
        verbose_name=_('内存GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('内存每GiB每天的价格'))
    vm_cpu = models.DecimalField(
        verbose_name=_('每CPU每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('每个CPU每天的价格'))
    vm_pub_ip = models.DecimalField(
        verbose_name=_('每公网IP每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('每个公网IP每天的价格'))
    vm_disk = models.DecimalField(
        verbose_name=_('系统盘GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('系统盘每GiB每天的价格'))
    vm_disk_snap = models.DecimalField(
        verbose_name=_('云盘快照GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('云盘快照每GiB每天的价格'))
    vm_upstream = models.DecimalField(
        verbose_name=_('云主机上行流量每GiB'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('云主机上行流量每GiB的价格'))
    vm_downstream = models.DecimalField(
        verbose_name=_('云主机下行流量每GiB'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('云主机下行流量每GiB的价格'))

    disk_size = models.DecimalField(
        verbose_name=_('云盘GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('云盘每GiB每天的价格'))
    disk_snap = models.DecimalField(
        verbose_name=_('云盘快照GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('云盘快照每GiB每天的价格'))

    obj_size = models.DecimalField(
        verbose_name=_('对象存储GiB每天'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储每GiB每天的价格'))
    obj_upstream = models.DecimalField(
        verbose_name=_('对象存储上行流量每GiB'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储上行流量每GiB的价格'))
    obj_downstream = models.DecimalField(
        verbose_name=_('对象存储下行流量每GiB'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储下行流量每GiB的价格'))
    obj_replication = models.DecimalField(
        verbose_name=_('对象存储同步流量每GiB'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储同步流量每GiB的价格'))
    obj_get_request = models.DecimalField(
        verbose_name=_('对象存储每万次get请求'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储每万次get请求'))
    obj_put_request = models.DecimalField(
        verbose_name=_('对象存储每万次put请求'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('对象存储每万次put请求'))
    prepaid_discount = models.PositiveSmallIntegerField(
        verbose_name=_('预付费折扣**%'), default=100, validators=(MaxValueValidator(100),),
        help_text=_('0-100, 包年包月预付费价格在按量计价的基础上按此折扣计价'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('资源计价定价')
        verbose_name_plural = verbose_name
        db_table = 'price'
        ordering = ['-creation_time']
