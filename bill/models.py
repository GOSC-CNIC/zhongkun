from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel, OwnerType, CustomIdModel
from utils.model import UuidModel, get_encryptor
from utils import rand_utils
from order.models import ResourceType
from users.models import UserProfile
from vo.models import VirtualOrganization
from service.models import ServiceConfig


class BasePointAccount(UuidModel):
    class Status(models.TextChoices):
        NORMAL = 'normal', _('正常')
        FROZEN = 'frozen', _('冻结')

    balance = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2, default='0.00')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    # status = models.CharField(
    #     verbose_name=_('状态'), max_length=16, choices=Status.choices, blank=True, default=Status.NORMAL.value)

    class Meta:
        abstract = True


class UserPointAccount(BasePointAccount):
    user = models.OneToOneField(to=UserProfile, on_delete=models.SET_NULL, null=True, default=None)

    class Meta:
        verbose_name = _('用户账户')
        verbose_name_plural = verbose_name
        db_table = 'user_point_account'
        ordering = ['-creation_time']

    def __repr__(self):
        if self.user:
            return f'UserPointAccount[{self.user.username}]<{self.balance}>'

        return f'UserPointAccount<{self.balance}>'


class VoPointAccount(BasePointAccount):
    vo = models.OneToOneField(to=VirtualOrganization, on_delete=models.SET_NULL, null=True, default=None)

    class Meta:
        verbose_name = _('VO组账户')
        verbose_name_plural = verbose_name
        db_table = 'vo_point_account'
        ordering = ['-creation_time']

    def __repr__(self):
        if self.vo:
            return f'VoPointAccount[{self.vo.name}]<{self.balance}>'

        return f'VoPointAccount<{self.balance}>'


class PayApp(CustomIdModel):
    class Status(models.TextChoices):
        UNAUDITED = 'unaudited', _('未审核')
        NORMAL = 'normal', _('正常')
        BAN = 'ban', _('禁止')

    name = models.CharField(verbose_name=_('应用名称'), max_length=256)
    app_url = models.CharField(verbose_name=_('应用网址'), max_length=256, blank=True, default='')
    app_desc = models.CharField(verbose_name=_('应用描述'), max_length=1024, blank=True, default='')
    rsa_public_key = models.CharField(verbose_name=_('RSA公钥'), max_length=2000, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    status = models.CharField(verbose_name=_('应用状态'), max_length=16, choices=Status.choices,
                              default=Status.UNAUDITED.value)

    class Meta:
        verbose_name = _('支付应用APP')
        verbose_name_plural = verbose_name
        db_table = 'app'
        ordering = ['-creation_time']

    def generate_id(self):
        return rand_utils.timestamp14_sn()

    def __str__(self):
        return self.name


class PayOrgnazition(CustomIdModel):
    """
    机构组织
    """
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    abbreviation = models.CharField(verbose_name=_('简称'), max_length=64, default='')
    independent_legal_person = models.BooleanField(verbose_name=_('是否独立法人单位'), default=True)
    country = models.CharField(verbose_name=_('国家/地区'), max_length=128, default='')
    city = models.CharField(verbose_name=_('城市'), max_length=128, default='')
    postal_code = models.CharField(verbose_name=_('邮政编码'), max_length=32, default='')
    address = models.CharField(verbose_name=_('单位地址'), max_length=256, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), null=True, blank=True, default=None)
    desc = models.CharField(verbose_name=_('描述'), blank=True, max_length=255)

    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')
    certification_url = models.CharField(verbose_name=_('机构认证代码url'), max_length=256,
                                         blank=True, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    user = models.ForeignKey(to=UserProfile, on_delete=models.SET_NULL, related_name='+', null=True, default=None)

    class Meta:
        ordering = ['creation_time']
        db_table = 'pay_orgnazition'
        verbose_name = _('机构')
        verbose_name_plural = verbose_name

    def generate_id(self):
        return f'o{rand_utils.timestamp14_sn()}'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'PayOrgnazition({self.name})'


class PayAppService(CustomIdModel):
    class Status(models.TextChoices):
        UNAUDITED = 'unaudited', _('未审核')
        NORMAL = 'normal', _('正常')
        BAN = 'ban', _('禁止')

    orgnazition = models.ForeignKey(
        verbose_name=_('机构|组织'), to=PayOrgnazition, on_delete=models.CASCADE, related_name='+')
    app = models.ForeignKey(verbose_name=_('应用APP'), to=PayApp, on_delete=models.CASCADE, related_name='+')
    name = models.CharField(verbose_name=_('服务名称'), max_length=256)
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    resources = models.CharField(verbose_name=_('服务提供的资源'), max_length=128, default='')
    desc = models.CharField(verbose_name=_('服务描述'), max_length=1024, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    status = models.CharField(verbose_name=_('服务状态'), max_length=16, choices=Status.choices,
                              default=Status.UNAUDITED.value)
    contact_person = models.CharField(verbose_name=_('联系人名称'), max_length=128,
                                      blank=True, default='')
    contact_email = models.EmailField(verbose_name=_('联系人邮箱'), blank=True, default='')
    contact_telephone = models.CharField(verbose_name=_('联系人电话'), max_length=16,
                                         blank=True, default='')
    contact_fixed_phone = models.CharField(verbose_name=_('联系人固定电话'), max_length=16,
                                           blank=True, default='')
    contact_address = models.CharField(verbose_name=_('联系人地址'), max_length=256,
                                       blank=True, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, on_delete=models.SET_NULL, related_name='+', null=True, default=None)

    class Meta:
        verbose_name = _('应用APP子服务')
        verbose_name_plural = verbose_name
        db_table = 'app_service'
        ordering = ['-creation_time']

    def generate_id(self):
        return f's{rand_utils.date8_random_digit_string(6)}'

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'PayAppService({self.name})'


class CashCouponBase(models.Model):
    face_value = models.DecimalField(verbose_name=_('面额'), max_digits=10, decimal_places=2)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    effective_time = models.DateTimeField(verbose_name=_('生效时间'))
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'))

    class Meta:
        abstract = True


class CashCouponActivity(UuidModel, CashCouponBase):
    class GrantStatus(models.TextChoices):
        WAIT = 'wait', _('待发放')
        GRANT = 'grant', _('发放中')
        COMPLETED = 'completed', _('发放完毕')

    name = models.CharField(verbose_name=_('活动名称'), max_length=255)
    app_service = models.ForeignKey(
        verbose_name=_('适用服务'), to=PayAppService, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None)
    grant_total = models.IntegerField(verbose_name=_('发放总数量'), default=0)
    granted_count = models.IntegerField(verbose_name=_('已发放数量'), default=0)
    grant_status = models.CharField(
        verbose_name=_('发放状态'), max_length=16, choices=GrantStatus.choices, default=GrantStatus.WAIT.value)
    desc = models.CharField(verbose_name=_('描述信息'), max_length=255, blank=True, default='')
    creator = models.CharField(verbose_name=_('创建人'), max_length=128, blank=True, default='')

    class Meta:
        verbose_name = _('代金券活动')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon_activity'
        ordering = ['-creation_time']

    def __str__(self):
        return self.name


class CashCoupon(CashCouponBase):
    class Status(models.TextChoices):
        WAIT = 'wait', _('未领取')
        AVAILABLE = 'available', _('有效')
        CANCELLED = 'cancelled', _('作废')
        DELETED = 'deleted', _('删除')

    id = models.CharField(verbose_name=_('编码'), max_length=32, primary_key=True, editable=False)
    app_service = models.ForeignKey(
        verbose_name=_('适用服务'), to=PayAppService, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None)
    balance = models.DecimalField(verbose_name=_('余额'), max_digits=10, decimal_places=2)
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    granted_time = models.DateTimeField(verbose_name=_('领取/发放时间'), null=True, blank=True, default=None)
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None)
    vo = models.ForeignKey(
        verbose_name=_('VO组'), to=VirtualOrganization, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None)
    owner_type = models.CharField(
        verbose_name=_('所属类型'), max_length=16, choices=OwnerType.choices + [('', _('未知'))], blank=True, default='')
    _coupon_code = models.CharField(verbose_name=_('券密码'), db_column='coupon_code', max_length=64)
    activity = models.ForeignKey(
        verbose_name=_('活动'), to=CashCouponActivity, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None
    )

    class Meta:
        verbose_name = _('代金券')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'CashCoupon({self.id})'

    def __str__(self):
        return self.id

    @staticmethod
    def generate_cash_coupon_id():
        return rand_utils.random_digit_string(16)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = self.generate_cash_coupon_id()
            force_insert = True

        if not self.coupon_code:
            self.coupon_code = rand_utils.random_letter_digit_string(8)

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @property
    def coupon_code(self):
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self._coupon_code)
        except encryptor.InvalidEncrypted as e:
            return None

    @coupon_code.setter
    def coupon_code(self, value: str):
        encryptor = get_encryptor()
        self._coupon_code = encryptor.encrypt(value)


class PaymentHistory(CustomIdModel):
    class Type(models.TextChoices):
        RECHARGE = 'recharge', _('充值')
        PAYMENT = 'payment', _('支付')
        REFUND = 'refund', _('退款')

    class PaymentMethod(models.TextChoices):
        BALANCE = 'balance', _('余额')
        CASH_COUPON = 'coupon', _('代金卷')
        BALANCE_COUPON = 'balance+coupon', _('余额+代金卷')

    payment_account = models.CharField(
        verbose_name=_('付款账户'), max_length=36, blank=True, default='',
        help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
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
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')

    order_id = models.CharField(verbose_name=_('订单ID'), max_length=36, blank=True, default='')
    resource_type = models.CharField(
        verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices, default=ResourceType.VM)
    app_service_id = models.CharField(verbose_name=_('APP服务ID'), max_length=36, blank=True, default='')
    instance_id = models.CharField(
        verbose_name=_('资源实例ID'), max_length=64, default='', help_text='云主机，硬盘id，存储桶名称')
    coupon_amount = models.DecimalField(
        verbose_name=_('券金额'), max_digits=10, decimal_places=2, help_text=_('代金券或者抵扣金额'), default=Decimal('0'))
    subject = models.CharField(verbose_name=_('标题'), max_length=256, default='')
    app_id = models.CharField(verbose_name=_('应用ID'), max_length=36, blank=True, default='')

    class Meta:
        verbose_name = _('支付记录')
        verbose_name_plural = verbose_name
        db_table = 'payment_history'
        ordering = ['-payment_time']
        indexes = [
            models.Index(fields=['payer_id'], name='idx_payer_id'),
        ]

    def __repr__(self):
        return f'PaymentHistory[{self.id}]<{self.get_type_display()}, {self.amounts}>'

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()


class CashCouponPaymentHistory(CustomIdModel):
    payment_history = models.ForeignKey(to=PaymentHistory, on_delete=models.SET_NULL, null=True)
    cash_coupon = models.ForeignKey(to=CashCoupon, on_delete=models.SET_NULL, null=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    amounts = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2)
    before_payment = models.DecimalField(verbose_name=_('支付前余额'), max_digits=10, decimal_places=2)
    after_payment = models.DecimalField(verbose_name=_('支付后余额'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('代金券扣费记录')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon_payment'
        ordering = ['-creation_time']

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()
