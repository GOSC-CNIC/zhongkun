from django.contrib import admin

from .models import (
    PaymentHistory, UserPointAccount, VoPointAccount, PayApp, CashCouponActivity, CashCoupon
)


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amounts', 'before_payment', 'after_payment', 'payment_time',
                    'payer_type', 'payer_id', 'payer_name', 'payment_method', 'payment_account', 'executor')
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
                    'service', 'grant_total', 'granted_count',
                    'grant_status', 'creation_time', 'desc')
    list_display_links = ('name',)
    list_select_related = ('service',)


@admin.register(CashCoupon)
class CashCouponAdmin(admin.ModelAdmin):
    list_display = ('id', 'activity', 'face_value', 'balance', 'effective_time', 'expiration_time', 'status',
                    'service', 'user', 'vo', 'owner_type',
                    'granted_time', 'coupon_code', 'creation_time')
    list_display_links = ('id',)
    list_select_related = ('service', 'user', 'vo', 'activity')
    raw_id_fields = ('activity', 'user', 'vo')
    readonly_fields = ('_coupon_code',)
