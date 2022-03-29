from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel, OwnerType
from order.models import ResourceType
from users.models import UserProfile
from vo.models import VirtualOrganization


class UserPointAccount(UuidModel):
    balance = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2, default='0.00')
    user = models.OneToOneField(to=UserProfile, on_delete=models.SET_NULL, null=True, default=None)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('用户账户')
        verbose_name_plural = verbose_name
        db_table = 'user_point_account'
        ordering = ['-creation_time']

    def __repr__(self):
        if self.user:
            return f'UserPointAccount[{self.user.username}]<{self.balance}>'

        return f'UserPointAccount<{self.balance}>'


class VoPointAccount(UuidModel):
    balance = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2, default='0.00')
    vo = models.OneToOneField(to=VirtualOrganization, on_delete=models.SET_NULL, null=True, default=None)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)

    class Meta:
        verbose_name = _('VO组账户')
        verbose_name_plural = verbose_name
        db_table = 'vo_point_account'
        ordering = ['-creation_time']

    def __repr__(self):
        if self.vo:
            return f'VoPointAccount[{self.vo.name}]<{self.balance}>'

        return f'VoPointAccount<{self.balance}>'


class Bill(UuidModel):
    class Type(models.TextChoices):
        METER = 'meter', _('计费')
        PREPAID = 'prepaid', _('预付费')
        REFUND = 'refund', _('退款')

    class Status(models.TextChoices):
        UNPAID = 'unpaid', _('待支付')
        PREPAID = 'prepaid', _('已支付')
        CANCELLED = 'cancelled', _('作废')

    type = models.CharField(verbose_name=_('账单类型'), max_length=16, choices=Type.choices)
    status = models.CharField(verbose_name=_('账单状态'), max_length=16, choices=Status.choices)
    amounts = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2)

    order_id = models.CharField(verbose_name=_('订单ID'), max_length=36, blank=True, default='')
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices)
    service_id = models.CharField(verbose_name=_('服务ID'), max_length=36, blank=True, default='')
    instance_id = models.CharField(verbose_name=_('资源实例ID'), max_length=36, default='')

    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)

    class Meta:
        verbose_name = _('账单')
        verbose_name_plural = verbose_name
        db_table = 'bill'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'Bill[{self.id}]<{self.get_type_display()}, {self.get_status_display()}, {self.amounts}>'


class PaymentHistory(UuidModel):
    class Type(models.TextChoices):
        RECHARGE = 'recharge', _('充值')
        PAYMENT = 'payment', _('支付')
        REFUND = 'refund', _('退款')

    class PaymentMethod(models.TextChoices):
        BALANCE = 'balance', _('余额')

    payment_account = models.CharField(
        verbose_name=_('付款账户'), max_length=36, blank=True, default='', help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
    payment_method = models.CharField(
        verbose_name=_('付款方式'), max_length=16, choices=PaymentMethod.choices, default=PaymentMethod.BALANCE)
    executor = models.CharField(
        verbose_name=_('交易执行人'), max_length=128, blank=True, default='', help_text=_('记录此次支付交易是谁执行完成的'))
    payer_id = models.CharField(verbose_name=_('付款人ID'), max_length=36, blank=True, default='',
                                help_text='user id or vo id')
    payer_name = models.CharField(verbose_name=_('付款人名称'), max_length=255, blank=True, default='',
                                  help_text='username or vo name')
    payer_type = models.CharField(verbose_name=_('付款人类型'), max_length=8, choices=OwnerType.choices)
    amounts = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2)
    before_payment = models.DecimalField(verbose_name=_('支付前余额'), max_digits=10, decimal_places=2)
    after_payment = models.DecimalField(verbose_name=_('支付后余额'), max_digits=10, decimal_places=2)
    payment_time = models.DateTimeField(verbose_name=_('支付时间'), auto_now_add=True)
    type = models.CharField(verbose_name=_('支付类型'), max_length=16, choices=Type.choices)
    bill = models.OneToOneField(to=Bill, on_delete=models.SET_NULL, null=True, blank=True, default=None)
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('支付记录')
        verbose_name_plural = verbose_name
        db_table = 'payment_history'
        ordering = ['-payment_time']

    def __repr__(self):
        return f'PaymentHistory[{self.id}]<{self.get_type_display()}, {self.amounts}>'
