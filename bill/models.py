from decimal import Decimal
from datetime import datetime

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone

from utils.model import UuidModel, OwnerType, CustomIdModel, get_encryptor
from utils import rand_utils
from users.models import UserProfile
from vo.models import VirtualOrganization
from core import errors


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
        verbose_name = _('支付机构')
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

    class Category(models.TextChoices):
        VMS_SERVER = 'vms-server', _('VMS云服务器')
        VMS_OBJECT = 'vms-object', _('VMS对象存储')
        VMS_MONITOR = 'vms-monitor', _('VMS监控')
        HIGH_CLOUD = 'high-cloud', _('高等级云')
        HPC = 'hpc', _('高性能计算')
        OTHER = 'other', _('其他')

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
    category = models.CharField(
        verbose_name=_('服务类别'), max_length=16, choices=Category.choices, default=Category.OTHER.value)
    service_id = models.CharField(verbose_name=_('对应的服务单元ID'), max_length=64, blank=True, default='')
    users = models.ManyToManyField(
        verbose_name=_('管理用户'), to=UserProfile, related_name='+', blank=True,
        db_constraint=False, db_table='pay_app_service_users')

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
        verbose_name = _('资源券活动/模板')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon_activity'
        ordering = ['-creation_time']

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.validate_availability()
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def validate_availability(self):
        """
        检验合理性可用性
        """
        if self.face_value <= Decimal('0'):
            raise errors.ValidationError(message=gettext('券面额必须大于0'))

        if self.effective_time is None or self.expiration_time is None:
            raise errors.ValidationError(message=gettext('生效时间或过期时间不能为空'))

        if self.effective_time >= self.expiration_time:
            raise errors.ValidationError(message=gettext('生效时间必须小于过期时间'))

        if self.expiration_time <= timezone.now():
            raise errors.ValidationError(message=gettext('过期时间必须大于当前时间'))

        if not self.app_service_id:
            raise errors.ValidationError(message=gettext('券必须绑定一个服务'))


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
    issuer = models.CharField(verbose_name=_('发放人'), max_length=128, blank=True, default='')
    balance_notice_time = models.DateTimeField(verbose_name=_('余额不足通知时间'), null=True, blank=True, default=None)
    expire_notice_time = models.DateTimeField(verbose_name=_('过期通知时间'), null=True, blank=True, default=None)

    class Meta:
        verbose_name = _('资源券')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon'
        ordering = ['-creation_time']

    def __repr__(self):
        return f'CashCoupon({self.id})'

    def __str__(self):
        return self.id

    @staticmethod
    def generate_cash_coupon_id(num: int = 0):
        """
        2-3位年 + 月 + 日 + 微妙数 或 一个指定整数
        """
        t = datetime.utcnow()
        if num > 0:
            s = f'{num:06}'
        else:
            s = f"{t.microsecond:06}"

        return f"{t.year % 1000}{t.month:02}{t.day:02}{s}"

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = self.generate_cash_coupon_id()
            force_insert = True

        if not self.coupon_code:
            self.coupon_code = rand_utils.random_digit_string(6)

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

    @property
    def one_exchange_code(self):
        """
        券编码和验证码拼接成一个兑换码
        """
        return f'{self.id}{self.coupon_code}'

    @staticmethod
    def parse_exchange_code(code: str):
        if len(code) <= 6:
            return '', code

        if '#' in code:     # 兼容以前格式的兑换码
            return code.rsplit('#', maxsplit=1)

        return code[0:-6], code[-6:]

    @classmethod
    def create_wait_draw_coupon(
            cls,
            app_service_id,
            face_value: Decimal,
            effective_time: datetime,
            expiration_time: datetime,
            coupon_num: int,
            issuer: str,
            activity_id: str = None
    ):
        """
        创建一个待领取的券

        coupon_num: 券日编号，大于0有效，其他默认使用当前时间微妙数

        :raises: Exception
        """
        coupon = cls(
            face_value=face_value,
            effective_time=effective_time,
            expiration_time=expiration_time,
            app_service_id=app_service_id,
            balance=face_value,
            status=CashCoupon.Status.WAIT.value,
            granted_time=timezone.now(),
            activity_id=activity_id,
            issuer=issuer,
        )

        if coupon_num:
            coupon.id = cls.generate_cash_coupon_id(num=coupon_num)

        try:
            coupon.save(force_insert=True)
        except Exception as e:
            raise e

        return coupon


class PaymentHistory(CustomIdModel):
    class Status(models.TextChoices):
        WAIT = 'wait', _('等待支付')
        SUCCESS = 'success', _('支付成功')
        ERROR = 'error', _('支付失败')
        CLOSED = 'closed', _('交易关闭')

    class PaymentMethod(models.TextChoices):
        BALANCE = 'balance', _('余额')
        CASH_COUPON = 'coupon', _('资源券')
        BALANCE_COUPON = 'balance+coupon', _('余额+资源券')

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
    payable_amounts = models.DecimalField(
        verbose_name=_('需付金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    amounts = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2)
    coupon_amount = models.DecimalField(
        verbose_name=_('券金额'), max_digits=10, decimal_places=2, help_text=_('资源券或者抵扣金额'), default=Decimal('0'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    payment_time = models.DateTimeField(verbose_name=_('支付时间'), null=True, default=None)
    status = models.CharField(
        verbose_name=_('支付状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    status_desc = models.CharField(verbose_name=_('支付状态描述'), max_length=255, default='')
    subject = models.CharField(verbose_name=_('标题'), max_length=256, default='')
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')
    order_id = models.CharField(verbose_name=_('订单ID'), max_length=36, blank=True, default='')
    app_service_id = models.CharField(verbose_name=_('APP服务ID'), max_length=36, blank=True, default='')
    app_id = models.CharField(verbose_name=_('应用ID'), max_length=36, blank=True, default='')
    instance_id = models.CharField(
        verbose_name=_('资源实例ID'), max_length=64, default='', help_text='云主机，硬盘id，存储桶名称')

    class Meta:
        verbose_name = _('支付记录')
        verbose_name_plural = verbose_name
        db_table = 'payment_history'
        ordering = ['-payment_time']
        indexes = [
            models.Index(fields=['payer_id'], name='idx_payer_id'),
            models.Index(fields=['order_id'], name='idx_order_id'),
        ]

    def __repr__(self):
        return f'PaymentHistory[{self.id}]<{self.get_status_display()}, {self.amounts}>'

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
        verbose_name = _('资源券扣费记录')
        verbose_name_plural = verbose_name
        db_table = 'cash_coupon_payment'
        ordering = ['-creation_time']

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()


class TransactionBill(CustomIdModel):
    """交易流水账单"""

    class TradeType(models.TextChoices):
        PAYMENT = 'payment', _('支付')
        RECHARGE = 'recharge', _('充值')
        REFUND = 'refund', _('退款')

    account = models.CharField(
        verbose_name=_('付款账户'), max_length=36, blank=True, default='',
        help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
    subject = models.CharField(verbose_name=_('标题'), max_length=256, default='')
    trade_type = models.CharField(verbose_name=_('交易类型'), max_length=16, choices=TradeType.choices)
    trade_id = models.CharField(verbose_name=_('交易id'), max_length=36, help_text=_('支付、退款、充值ID'))
    out_trade_no = models.CharField(
        verbose_name=_('外部交易编号'), max_length=64, default='', help_text=_('支付订单号、退款单号'))
    trade_amounts = models.DecimalField(
        verbose_name=_('交易总金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('余额+券金额'))
    amounts = models.DecimalField(verbose_name=_('金额'), max_digits=10, decimal_places=2, help_text='16.66, -8.88')
    coupon_amount = models.DecimalField(
        verbose_name=_('券金额'), max_digits=10, decimal_places=2, default=Decimal('0'), help_text=_('资源券或者抵扣金额'))
    after_balance = models.DecimalField(verbose_name=_('交易后余额'), max_digits=10, decimal_places=2)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')
    owner_id = models.CharField(verbose_name=_('所属人ID'), max_length=36, blank=True, default='',
                                help_text='user id or vo id')
    owner_name = models.CharField(verbose_name=_('所属人名称'), max_length=255, blank=True, default='',
                                  help_text='username or vo name')
    owner_type = models.CharField(verbose_name=_('所属人类型'), max_length=8, choices=OwnerType.choices)
    app_service_id = models.CharField(verbose_name=_('APP服务ID'), max_length=36, blank=True, default='')
    app_id = models.CharField(verbose_name=_('应用ID'), max_length=36, blank=True, default='')
    operator = models.CharField(
        verbose_name=_('交易操作人'), max_length=128, blank=True, default='', help_text=_('记录此次支付交易是谁执行完成的'))

    class Meta:
        verbose_name = _('交易流水账单')
        verbose_name_plural = verbose_name
        db_table = 'transaction_bill'
        ordering = ['-creation_time']
        indexes = [
            models.Index(fields=['owner_id'], name='idx_owner_id'),
            models.Index(fields=['trade_id'], name='idx_trade_id'),
        ]

    def __repr__(self):
        return f'TransactionBill[{self.id}]<{self.get_trade_type_display()}, {self.amounts}>'

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()


class RefundRecord(CustomIdModel):
    """退款记录"""

    class Status(models.TextChoices):
        WAIT = 'wait', _('等待退款')
        SUCCESS = 'success', _('退款成功')
        ERROR = 'error', _('退款失败')
        CLOSED = 'closed', _('交易关闭')

    trade_id = models.CharField(verbose_name=_('支付交易记录ID'), max_length=36, blank=True, default='')
    out_order_id = models.CharField(verbose_name=_('外部订单编号'), max_length=36, blank=True, default='')
    out_refund_id = models.CharField(verbose_name=_('外部退款单编号'), max_length=64, blank=True, default='')
    refund_reason = models.CharField(verbose_name=_('退款原因'), max_length=255, blank=True, default='')
    total_amounts = models.DecimalField(verbose_name=_('退款对应的交易订单总金额'), max_digits=10, decimal_places=2)
    refund_amounts = models.DecimalField(verbose_name=_('申请退款金额'), max_digits=10, decimal_places=2)
    real_refund = models.DecimalField(verbose_name=_('实际退款金额'), max_digits=10, decimal_places=2)
    coupon_refund = models.DecimalField(
        verbose_name=_('资源券退款金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('资源券或者优惠抵扣金额，此金额不退'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    success_time = models.DateTimeField(verbose_name=_('退款成功时间'), null=True, default=None)
    status = models.CharField(
        verbose_name=_('退款状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    status_desc = models.CharField(verbose_name=_('退款状态描述'), max_length=255, default='')
    remark = models.CharField(verbose_name=_('备注信息'), max_length=256, default='')
    app_service_id = models.CharField(verbose_name=_('APP服务ID'), max_length=36, blank=True, default='')
    app_id = models.CharField(verbose_name=_('应用ID'), max_length=36, blank=True, default='')
    in_account = models.CharField(
        verbose_name=_('入账账户'), max_length=36, blank=True, default='',
        help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
    owner_id = models.CharField(verbose_name=_('所属人ID'), max_length=36, blank=True, default='',
                                help_text='user id or vo id')
    owner_name = models.CharField(verbose_name=_('所属人名称'), max_length=255, blank=True, default='',
                                  help_text='username or vo name')
    owner_type = models.CharField(verbose_name=_('所属人类型'), max_length=8, choices=OwnerType.choices)
    operator = models.CharField(
        verbose_name=_('交易操作人'), max_length=128, blank=True, default='', help_text=_('记录此次支付交易是谁执行完成的'))

    class Meta:
        verbose_name = _('退款记录')
        verbose_name_plural = verbose_name
        db_table = 'refund_record'
        ordering = ['-creation_time']
        indexes = [
            models.Index(fields=['trade_id'], name='idx_refund_trade_id'),
            models.Index(fields=['out_refund_id'], name='idx_refund_out_refund_id'),
        ]

    def __repr__(self):
        return f'RefundRecord[{self.id}]<{self.get_status_display()}, {self.real_refund}>'

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()

    def set_refund_sucsess(self, in_account: str):
        self.status = self.Status.SUCCESS.value
        self.success_time = timezone.now()
        self.status_desc = '退款成功'
        self.in_account = in_account
        self.save(update_fields=['status', 'success_time', 'status_desc', 'in_account'])


class Recharge(CustomIdModel):
    """充值记录"""

    class Status(models.TextChoices):
        WAIT = 'wait', _('待充值')     # 待支付（支付宝或微信）
        SUCCESS = 'success', _('支付成功')  # 支付宝或微信支付成功
        ERROR = 'error', _('支付失败')  # 支付宝或微信支付失败
        CLOSED = 'closed', _('交易关闭')    # 关闭了本次充值
        COMPLETE = 'complete', _('充值完成')    # 成功充值到用户余额账户

    class TradeChannel(models.TextChoices):
        MANUAL = 'manual', _('人工充值')
        WECHAT = 'wechat', _('微信支付')
        ALIPAY = 'alipay', _('支付宝')

    trade_channel = models.CharField(
        verbose_name=_('交易渠道'), max_length=16, choices=TradeChannel.choices, default=TradeChannel.MANUAL.value)
    out_trade_no = models.CharField(verbose_name=_('外部交易编号'), max_length=64, blank=True, default='')
    channel_account = models.CharField(verbose_name=_('交易渠道账户编号'), max_length=64, blank=True, default='')
    channel_fee = models.DecimalField(verbose_name=_('交易渠道费用'), max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(verbose_name=_('充值总金额'), max_digits=10, decimal_places=2)
    receipt_amount = models.DecimalField(
        verbose_name=_('实收金额'), max_digits=10, decimal_places=2, help_text=_('交易渠道中我方账户实际收到的款项'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    success_time = models.DateTimeField(verbose_name=_('充值成功时间'), null=True, default=None)
    status = models.CharField(
        verbose_name=_('充值状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    status_desc = models.CharField(verbose_name=_('充值状态描述'), max_length=255, default='')
    in_account = models.CharField(
        verbose_name=_('入账账户'), max_length=36, blank=True, default='',
        help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
    owner_id = models.CharField(verbose_name=_('所属人ID'), max_length=36, blank=True, default='',
                                help_text='user id or vo id')
    owner_name = models.CharField(verbose_name=_('所属人名称'), max_length=255, blank=True, default='',
                                  help_text='username or vo name')
    owner_type = models.CharField(verbose_name=_('所属人类型'), max_length=8, choices=OwnerType.choices)
    remark = models.CharField(verbose_name=_('备注信息'), max_length=256, default='')
    executor = models.CharField(
        verbose_name=_('交易执行人'), max_length=128, blank=True, default='', help_text=_('记录此次支付交易是谁执行完成的'))

    class Meta:
        verbose_name = _('充值记录')
        verbose_name_plural = verbose_name
        db_table = 'wallet_recharge'
        ordering = ['-creation_time']
        indexes = [
            models.Index(fields=['owner_id'], name='idx_recharge_owner_id'),
        ]

    def __repr__(self):
        return f'Recharge[{self.id}]<{self.get_status_display()}, {self.total_amount}>'

    def generate_id(self):
        return rand_utils.timestamp20_rand4_sn()
