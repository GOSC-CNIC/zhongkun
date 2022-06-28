from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    PaymentHistory, UserPointAccount, VoPointAccount, PayApp, CashCouponActivity, CashCoupon,
    PayOrgnazition, PayAppService
)


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
class PayAppAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'status', 'creation_time', 'app_url')
    list_display_links = ('id',)


@admin.register(CashCouponActivity)
class CashCouponActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'face_value', 'effective_time', 'expiration_time',
                    'app_service', 'grant_total', 'granted_count',
                    'grant_status', 'creation_time', 'desc')
    list_display_links = ('name',)
    list_select_related = ('app_service',)


@admin.register(CashCoupon)
class CashCouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity', 'face_value', 'balance', 'effective_time', 'expiration_time', 'status',
                    'app_service', 'user', 'vo', 'owner_type',
                    'granted_time', 'exchange_code', 'creation_time')
    list_display_links = ('id',)
    list_select_related = ('app_service', 'user', 'vo', 'activity')
    raw_id_fields = ('activity', 'user', 'vo')
    readonly_fields = ('_coupon_code',)

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
class PayAppServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'name_en', 'creation_time', 'status', 'resources', 'contact_person',
                    'contact_email', 'contact_telephone', 'desc')
    list_display_links = ('id',)
    list_select_related = ('orgnazition', 'app')
    raw_id_fields = ('user',)
