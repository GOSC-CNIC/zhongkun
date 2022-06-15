from django.contrib import admin

from .models import CashCouponActivity, CashCoupon


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
