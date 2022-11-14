from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from django import forms

from utils.model import NoDeleteSelectModelAdmin
from .models import (
    PaymentHistory, UserPointAccount, VoPointAccount, PayApp, CashCouponActivity, CashCoupon,
    PayOrgnazition, PayAppService
)
from .managers import CashCouponActivityManager


class PayAppForm(forms.ModelForm):
    class Meta:
        widgets = {
            'rsa_public_key': forms.Textarea(attrs={'cols': 80, 'rows': 6}),
        }


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'subject', 'type', 'payment_method', 'amounts', 'coupon_amount',
                    'before_payment', 'after_payment', 'payment_time', 'app_id',
                    'payer_type', 'payer_id', 'payer_name', 'payment_account', 'executor')
    list_display_links = ('id',)
    list_filter = ('type', 'payer_type')
    search_fields = ('id', 'payer_id', 'payer_name')


@admin.register(UserPointAccount)
class UserPointAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'user',)
    list_display_links = ('id',)
    list_select_related = ('user',)
    readonly_fields = ('balance',)


@admin.register(VoPointAccount)
class VoPointAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'vo')
    list_display_links = ('id',)
    list_select_related = ('vo',)
    readonly_fields = ('balance',)


@admin.register(PayApp)
class PayAppAdmin(NoDeleteSelectModelAdmin):
    form = PayAppForm
    list_display = ('id', 'name', 'status', 'creation_time', 'app_url')
    list_display_links = ('id',)


@admin.register(CashCouponActivity)
class CashCouponActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'face_value', 'effective_time', 'expiration_time',
                    'app_service', 'grant_total', 'granted_count',
                    'grant_status', 'creation_time', 'desc')
    list_display_links = ('name',)
    list_select_related = ('app_service',)
    actions = ['create_coupon_for_activity']

    @admin.action(description=_('为券模板/活动生成券'))
    def create_coupon_for_activity(self, request, queryset):
        length = len(queryset)
        if length == 0:
            self.message_user(request=request, message='你没有选中任何一个券模板/活动', level=messages.ERROR)
            return
        if length > 1:
            self.message_user(request=request, message='每次只能选中一个券模板/活动', level=messages.ERROR)
            return

        obj = queryset[0]
        try:
            ay, count, err = CashCouponActivityManager().create_coupons_for_template(
                activity_id=obj.id, user=request.user, max_count=50
            )
            if err is not None:
                msg = '为券模板/活动生成券错误（%(error)s），本次成功生成券数量:%(count)d个。' % {
                    'error': str(err), 'count': count
                }
                self.message_user(request=request, message=msg, level=messages.ERROR)
                return
        except Exception as e:
            self.message_user(request=request, message=f'为券模板/活动生成券错误，{str(e)}', level=messages.ERROR)
            return

        self.message_user(request=request, message=_('成功生成券') + f':{count}', level=messages.SUCCESS)


@admin.register(CashCoupon)
class CashCouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity', 'face_value', 'balance', 'effective_time', 'expiration_time', 'status',
                    'app_service', 'user', 'vo', 'owner_type',
                    'granted_time', 'exchange_code', 'creation_time')
    list_display_links = ('id',)
    list_select_related = ('app_service', 'user', 'vo', 'activity')
    raw_id_fields = ('activity', 'user', 'vo')
    readonly_fields = ('_coupon_code',)
    list_filter = ('app_service', 'app_service__category')
    search_fields = ('id', 'user__username')

    @admin.display(description=_('兑换码'))
    def exchange_code(self, obj):
        return obj.one_exchange_code


@admin.register(PayOrgnazition)
class PayOrgnazitionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_en', 'abbreviation', 'independent_legal_person', 'country',
                    'city', 'postal_code', 'address', 'creation_time', 'desc')
    list_display_links = ('id',)
    raw_id_fields = ('user',)


@admin.register(PayAppService)
class PayAppServiceAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'name', 'name_en', 'category', 'service', 'creation_time', 'status', 'user',
                    'resources', 'contact_person', 'contact_email', 'contact_telephone', 'desc')
    list_display_links = ('id',)
    list_select_related = ('orgnazition', 'app', 'service', 'user')
    raw_id_fields = ('user',)
