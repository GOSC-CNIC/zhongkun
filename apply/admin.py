from django.contrib import admin

from apply.models import CouponApply
from utils.model import BaseModelAdmin


@admin.register(CouponApply)
class CouponApplyAdmin(BaseModelAdmin):
    list_display = ['id', 'service_type', 'odc', 'service_name', 'face_value', 'expiration_time',
                    'apply_desc', 'creation_time', 'username', 'vo_name', 'owner_type',
                    'status', 'approver', 'approved_amount', 'reject_reason', 'deleted', 'coupon_id']
    list_display_links = ('id',)
    list_select_related = ('odc',)
    list_filter = ('service_type', 'status', 'owner_type', 'deleted')
    search_fields = ('service_name', 'username', 'vo_name', 'approver')
