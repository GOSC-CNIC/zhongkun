import random
from decimal import Decimal

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError

from apps.servers.models import ServiceConfig
from utils.model import UuidModel, OwnerType, PayType, ResourceType, CustomIdModel
from utils import rand_utils


def generate_order_sn():
    """
    生成订单编号
    长22位: 日期+纳秒+2位随机数
    """
    t = timezone.now()
    rand = random.randint(0, 99)
    return f"{t.year:04}{t.month:02}{t.day:02}{t.hour:02}{t.minute:02}{t.second:02}{t.microsecond:06}{rand:02}"


class Order(models.Model):
    OwnerType = OwnerType

    class OrderType(models.TextChoices):
        NEW = 'new', _('新购')
        RENEWAL = 'renewal', _('续费')
        UPGRADE = 'upgrade', _('升级')
        DOWNGRADE = 'downgrade', _('降级')
        POST2PRE = 'post2pre', _('按量付费转包年包月')

    class Status(models.TextChoices):
        PAID = 'paid', _('已支付')
        UNPAID = 'unpaid', _('未支付')
        CANCELLED = 'cancelled', _('作废')
        REFUND = 'refund', _('全额退款')
        PART_REFUND = 'partrefund', _('部分退款')
        REFUNDING = 'refunding', _('退款中')

    class PaymentMethod(models.TextChoices):
        UNKNOWN = 'unknown', _('未知')
        BALANCE = 'balance', _('余额')
        CASH_COUPON = 'cashcoupon', _('资源券')
        MIXED = 'mixed', _('混合支付')

    class TradingStatus(models.TextChoices):
        OPENING = 'opening', _('交易中')
        UNDELIVERED = 'undelivered', _('订单资源交付失败')
        COMPLETED = 'completed', _('交易成功')
        CLOSED = 'closed', _('交易关闭')
        PART_DELIVER = 'partdeliver', _('部分交付失败')

    class OrderAction(models.TextChoices):
        NONE = 'none', _('无')
        DELIVERING = 'delivering', _('正在交付订单资源')

    class PeriodUnit(models.TextChoices):
        DAY = 'day', _('天')
        MONTH = 'month', _('月')

    id = models.CharField(verbose_name=_('订单编号'), max_length=32, primary_key=True, editable=False)
    order_type = models.CharField(
        verbose_name=_('订单类型'), max_length=16, choices=OrderType.choices, default=OrderType.NEW)
    status = models.CharField(
        verbose_name=_('订单状态'), max_length=16, choices=Status.choices, default=Status.PAID)
    total_amount = models.DecimalField(
        verbose_name=_('原价金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('原价，折扣前的价格')
    )
    payable_amount = models.DecimalField(
        verbose_name=_('应付金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('需要支付的金额，扣除优惠或折扣后的金额')
    )
    pay_amount = models.DecimalField(
        verbose_name=_('实付金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('实际交易金额')
    )
    balance_amount = models.DecimalField(
        verbose_name=_('余额支付金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    coupon_amount = models.DecimalField(
        verbose_name=_('券支付金额'), max_digits=10, decimal_places=2, default=Decimal('0'))

    service_id = models.CharField(verbose_name=_('服务id'), max_length=36, blank=True, default='')
    service_name = models.CharField(verbose_name=_('服务名称'), max_length=255, blank=True, default='')
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices, default=ResourceType.VM)
    instance_config = models.JSONField(verbose_name=_('资源的规格和配置'), null=False, blank=True, default=dict)
    period = models.IntegerField(verbose_name=_('订购时长'), blank=True, default=0)
    period_unit = models.CharField(
        verbose_name=_('订购时长单位'), max_length=8, choices=PeriodUnit.choices, default=PeriodUnit.MONTH.value)

    payment_time = models.DateTimeField(verbose_name=_('支付时间'), null=True, blank=True, default=None)
    pay_type = models.CharField(verbose_name=_('结算方式'), max_length=16, choices=PayType.choices)
    payment_method = models.CharField(
        verbose_name=_('付款方式'), max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.UNKNOWN)

    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    start_time = models.DateTimeField(
        verbose_name=_('订购起始时间'), null=True, blank=True, default=None,
        help_text=_('包年包月订单订购资源的时间段起始时间')
    )
    end_time = models.DateTimeField(
        verbose_name=_('订购截止时间'), null=True, blank=True, default=None,
        help_text=_('包年包月订单订购资源的时间段截止时间')
    )
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=64, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=256, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)

    completion_time = models.DateTimeField(verbose_name=_('交易完成时间'), null=True, blank=True, default=None)
    trading_status = models.CharField(
        verbose_name=_('交易状态'), max_length=16, choices=TradingStatus.choices, default=TradingStatus.OPENING.value)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)
    cancelled_time = models.DateTimeField(verbose_name=_('作废时间'), null=True, blank=True, default=None)
    app_service_id = models.CharField(verbose_name=_('app服务id'), max_length=36, blank=True, default='')
    payment_history_id = models.CharField(verbose_name=_('支付记录id'), max_length=36, blank=True, default='')
    number = models.PositiveIntegerField(verbose_name=_('订购资源数量'), default=1)
    order_action = models.CharField(
        verbose_name=_('资源交付动作'), max_length=16, choices=OrderAction.choices, default=OrderAction.NONE.value,
        help_text=_('用于记录订单当前的操作动作，比如是否正在交付资源中，防止并发时订单业务冲突')
    )
    description = models.CharField(verbose_name=_('描述'), max_length=255, blank=True, default='')

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

    def set_paid(
            self, pay_amount: Decimal,
            balance_amount: Decimal,
            coupon_amount: Decimal,
            payment_history_id: str
    ):
        if balance_amount < Decimal('0') or coupon_amount < Decimal('0'):
            raise Exception(gettext('更新订单支付状态错误，balance_amount和coupon_amount不能为负数'))

        if balance_amount > Decimal('0') and coupon_amount == Decimal('0'):
            payment_method = self.PaymentMethod.BALANCE.value
        elif balance_amount == Decimal('0') and coupon_amount > Decimal('0'):
            payment_method = self.PaymentMethod.CASH_COUPON.value
        elif balance_amount > Decimal('0') and coupon_amount > Decimal('0'):
            payment_method = self.PaymentMethod.MIXED.value
        else:
            payment_method = self.PaymentMethod.UNKNOWN.value

        self.pay_amount = pay_amount
        self.balance_amount = balance_amount
        self.coupon_amount = coupon_amount
        self.status = self.Status.PAID.value
        self.payment_method = payment_method
        self.payment_time = timezone.now()
        self.payment_history_id = payment_history_id
        self.save(update_fields=[
            'pay_amount', 'balance_amount', 'coupon_amount', 'status', 'payment_method', 'payment_time',
            'payment_history_id'
        ])

    def set_cancel(self):
        self.status = self.Status.CANCELLED.value
        self.trading_status = self.TradingStatus.CLOSED.value
        self.cancelled_time = timezone.now()
        self.save(update_fields=['status', 'trading_status', 'cancelled_time'])

    def build_subject(self):
        if self.resource_type in ResourceType:
            resource_type = ResourceType(self.resource_type).label
        else:
            resource_type = gettext('未知资源')

        order_type = self.get_order_type_display()
        subject = f'{resource_type}({order_type})'
        if self.period > 0:
            subject += gettext('时长%d月') % (self.period,)

        return subject

    def get_pay_app_service_id(self):
        return self.app_service_id

    def clean(self):
        if not (1 <= self.number <= 3):
            raise ValidationError(message={'number': gettext('可选数值为1-3')})

    def set_order_action(self, act: str, is_save: bool = True):
        """
        使用此函数时需要确保此对象加锁
        """
        if act not in self.OrderAction.values:
            raise Exception(gettext('无效的订单动作标记'))

        if self.order_action == act:
            return

        self.order_action = act
        if is_save:
            self.save(update_fields=['order_action'])

    def set_completed(self):
        update_fields = ['trading_status', 'completion_time']
        self.trading_status = self.TradingStatus.COMPLETED.value
        self.completion_time = timezone.now()
        try:
            self.save(update_fields=update_fields)
        except Exception as e:
            message = gettext('更新订单交易状态失败') + str(e)
            raise Exception(message)


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
    delivered_time = models.DateTimeField(verbose_name=_('资源交付时间'), null=True, blank=True, default=None)
    instance_delete_time = models.DateTimeField(
        verbose_name=_('资源删除时间'), null=True, blank=True, default=None,
        help_text=_('不为空时，表示对应的资源删除的时间')
    )

    class Meta:
        verbose_name = _('订单资源')
        verbose_name_plural = verbose_name
        db_table = 'order_resource'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'Resource([{self.resource_type}]{self.instance_id})'

    def set_deliver_failed(self, failed_msg: str, raise_exc: bool = True):
        try:
            self.instance_status = self.InstanceStatus.FAILED.value
            self.desc = failed_msg
            self.save(update_fields=['instance_status', 'desc'])
        except Exception as e:
            if raise_exc:
                return e

    @staticmethod
    def set_many_deliver_failed(res_ids: list, failed_msg: str, raise_exc: bool = True):
        try:
            if len(failed_msg) >= 255:
                failed_msg = failed_msg[0:254]

            if len(res_ids) == 1:
                qs = Resource.objects.filter(id=res_ids[0])
            else:
                qs = Resource.objects.filter(id__in=res_ids)

            qs.update(instance_status=Resource.InstanceStatus.FAILED.value, desc=failed_msg)
        except Exception as e:
            if raise_exc:
                return e

    def set_deliver_success(self, instance_id: str = None, raise_exc: bool = True):
        try:
            self.instance_status = self.InstanceStatus.SUCCESS.value
            self.desc = 'success'
            self.delivered_time = timezone.now()
            update_fields = ['instance_status', 'desc', 'delivered_time']
            if instance_id:
                self.instance_id = instance_id
                update_fields.append('instance_id')

            self.save(update_fields=update_fields)
        except Exception as e:
            if raise_exc:
                return e


class Price(UuidModel):
    vm_base = models.DecimalField(
        verbose_name=_('每小时云主机基础维护费'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('每小时云主机基础维护费价格'))
    vm_ram = models.DecimalField(
        verbose_name=_('内存GiB每小时'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('内存每GiB每小时的价格'))
    vm_cpu = models.DecimalField(
        verbose_name=_('每CPU每小时'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('每个CPU每小时的价格'))
    vm_pub_ip = models.DecimalField(
        verbose_name=_('每公网IP每小时保有费'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('每个公网IP每小时的保有费价格'))
    vm_disk = models.DecimalField(
        verbose_name=_('系统盘GiB每小时'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('系统盘每GiB每小时的价格'))
    vm_disk_snap = models.DecimalField(
        verbose_name=_('系统盘快照GiB每小时'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        help_text=_('系统盘快照每GiB每小时的价格'))
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
    mntr_site_base = models.DecimalField(
        verbose_name=_('站点监控每天基础费用'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('站点监控每天基础监控费用'))
    mntr_site_tamper = models.DecimalField(
        verbose_name=_('站点监控每天防篡改费用'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('站点监控每天防篡改监控费用'))
    mntr_site_security = models.DecimalField(
        verbose_name=_('站点监控每天安全监控费用'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('站点监控每天安全监控费用'))
    scan_web = models.DecimalField(
        verbose_name=_('站点安全扫描每次费用'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('安全扫描WEB每次费用'))
    scan_host = models.DecimalField(
        verbose_name=_('主机安全扫描每次费用'), max_digits=10, decimal_places=5, validators=(MinValueValidator(0),),
        default=Decimal('0'), help_text=_('安全扫描host主机每次费用'))

    class Meta:
        verbose_name = _('资源计价定价')
        verbose_name_plural = verbose_name
        db_table = 'price'
        ordering = ['-creation_time']


class Period(CustomIdModel):
    period = models.PositiveSmallIntegerField(
        verbose_name=_('月数'), validators=(MinValueValidator(1), MaxValueValidator(120)))
    enable = models.BooleanField(verbose_name=_('可用状态'), default=True)
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    service = models.ForeignKey(
        to=ServiceConfig, on_delete=models.SET_NULL, db_constraint=False, db_index=False,
        related_name='+', null=True, blank=True, default=None, verbose_name=_('服务单元'))

    class Meta:
        db_table = 'order_period'
        ordering = ['period']
        verbose_name = _('订购时长')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Period({self.period})'

    def generate_id(self) -> str:
        return rand_utils.timestamp14_microsecond2_sn()


class OrderRefund(models.Model):
    class Status(models.TextChoices):
        WAIT = 'wait', _('待退款')
        REFUNDED = 'refunded', _('已退款')
        FAILED = 'failed', _('退款失败')
        CANCELLED = 'cancelled', _('取消')

    id = models.CharField(verbose_name=_('退订编号'), max_length=32, primary_key=True, editable=False)
    order = models.ForeignKey(verbose_name=_('退订订单'), to=Order, on_delete=models.PROTECT, related_name='+')
    order_amount = models.DecimalField(
        verbose_name=_('订单总金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    payment_history_id = models.CharField(verbose_name=_('支付记录id'), max_length=36, blank=True, default='')
    status = models.CharField(
        verbose_name=_('退订状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    status_desc = models.CharField(verbose_name=_('退订状态描述'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('退订时间'))
    update_time = models.DateTimeField(verbose_name=_('修改时间'))
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices, default=ResourceType.VM.value)
    number = models.PositiveIntegerField(verbose_name=_('退订资源数量'), default=1)
    reason = models.CharField(verbose_name=_('退订原因'), max_length=255, blank=True, default="")
    refund_amount = models.DecimalField(
        verbose_name=_('退款金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('需要退款的金额')
    )
    balance_amount = models.DecimalField(
        verbose_name=_('余额退款金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    coupon_amount = models.DecimalField(
        verbose_name=_('券退款金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    refund_history_id = models.CharField(verbose_name=_('退款记录id'), max_length=36, blank=True, default='')
    refunded_time = models.DateTimeField(verbose_name=_('退款完成时间'), null=True, blank=True, default=None)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=64, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=256, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)

    class Meta:
        verbose_name = _('退订退款')
        verbose_name_plural = verbose_name
        db_table = 'order_refund'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'OrderRefund[{self.id}]'

    def __str__(self):
        return f'[{self.id}]({self.get_status_display()}, {self.refund_amount})'

    @staticmethod
    def generate_refund_sn():
        return generate_order_sn()

    def enforce_refund_id(self):
        if not self.id:
            self.id = self.generate_refund_sn()

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        self.enforce_refund_id()
        return super().save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)
