from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core import exceptions
from django import forms

from utils.model import UuidModel, get_encryptor
from utils import rand_utils
from users.models import UserProfile
from service.models import ServiceConfig
from order.models import ResourceType, OwnerType
from vo.models import VirtualOrganization


class FormJSONMultipleChoiceField(forms.MultipleChoiceField):
    def __init__(self, *, choices=(), encoder=None, decoder=None, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices

    def bound_data(self, data, initial):
        if isinstance(data, str):
            return super().bound_data(data=data, initial=initial)

        return data


class ApplicableResourceField(models.JSONField):
    UNIVERSAL_VALUE = 'universal'
    UNIVERSAL_NAME = _('通用')

    def formfield(self, **kwargs):
        choices = ResourceType.choices + [(self.UNIVERSAL_VALUE, self.UNIVERSAL_NAME)]
        return super().formfield(**{
            'form_class': FormJSONMultipleChoiceField,
            'choices': choices,
            **kwargs,
        })

    def validate(self, value, model_instance):
        super().validate(value, model_instance)

        if self.UNIVERSAL_VALUE in value:
            if len(value) != 1:
                raise exceptions.ValidationError(
                    message=_('“%(value)r”不能与其他资源类型同时指定。') % {'value': self.UNIVERSAL_NAME})

        for val in value:
            if val not in ResourceType.values + [self.UNIVERSAL_VALUE]:
                raise exceptions.ValidationError(
                    self.error_messages['invalid_choice'],
                    code='invalid_choice',
                    params={'value': value},
                )


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
    service = models.ForeignKey(
        verbose_name=_('适用服务'), to=ServiceConfig, on_delete=models.SET_NULL, related_name='+',
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
    service = models.ForeignKey(
        verbose_name=_('适用服务'), to=ServiceConfig, on_delete=models.SET_NULL, related_name='+',
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
