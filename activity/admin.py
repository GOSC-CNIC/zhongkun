from django.contrib import admin
from django import forms
from django.core import exceptions
from django.utils.translation import gettext as _

from order.models import ResourceType
from .models import CashCouponActivity, CashCoupon, ApplicableResourceField, CouponType


class CashCouponModelForm(forms.ModelForm):
    def clean(self):
        data = super().clean()
        if data.get('coupon_type', '') == CouponType.UNIVERSAL.value:
            if data.get('service', None):
                raise exceptions.ValidationError(message=_('"通用"类型的代金券不能同时指定适用服务'))
        elif data.get('coupon_type', '') == CouponType.SPECIAL.value:
            if not data.get('service', None):
                raise exceptions.ValidationError(message=_('"专用"类型的代金券必须同时指定适用服务'))


class CashCouponBaseAdmin(admin.ModelAdmin):
    form = CashCouponModelForm

    @admin.display(
        description='适用资源'
    )
    def get_applicable_resource(self, obj):
        if not obj.applicable_resource:
            return [ApplicableResourceField.UNIVERSAL_NAME]

        disp = []
        choices_dict = {k: n for k, n in ResourceType.choices}
        choices_dict[ApplicableResourceField.UNIVERSAL_VALUE] = ApplicableResourceField.UNIVERSAL_NAME
        for val in obj.applicable_resource:
            name = choices_dict.get(val, val)
            disp.append(name)

        return disp


@admin.register(CashCouponActivity)
class CashCouponActivityAdmin(CashCouponBaseAdmin):
    list_display = ('id', 'name', 'face_value', 'effective_time', 'expiration_time',
                    'coupon_type', 'get_applicable_resource', 'service', 'grant_total', 'granted_count',
                    'grant_status', 'creation_time', 'desc')
    list_display_links = ('name',)
    list_select_related = ('service',)


@admin.register(CashCoupon)
class CashCouponAdmin(CashCouponBaseAdmin):
    list_display = ('id', 'activity', 'face_value', 'balance', 'effective_time', 'expiration_time', 'status',
                    'coupon_type', 'get_applicable_resource', 'service', 'user', 'vo', 'owner_type',
                    'granted_time', 'coupon_code', 'creation_time')
    list_display_links = ('id',)
    list_select_related = ('service', 'user', 'vo', 'activity')
    raw_id_fields = ('activity', 'user', 'vo')
    readonly_fields = ('_coupon_code',)
