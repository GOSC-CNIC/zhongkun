from django.contrib import admin
from django.utils.translation import gettext_lazy

from apply.models import CouponApply
from utils.model import NoDeleteSelectModelAdmin


@admin.register(CouponApply)
class CouponApplyAdmin(NoDeleteSelectModelAdmin):
    list_display = ['id', 'service_type', 'odc', 'service_name', 'face_value', 'expiration_time',
                    'apply_desc', 'creation_time', 'username', 'vo_name', 'owner_type', 'status',
                    'approver', 'approved_amount', 'reject_reason', 'show_deleted', 'delete_user', 'coupon_id']
    list_display_links = ('id',)
    list_select_related = ('odc',)
    list_filter = ('service_type', 'status', 'owner_type', 'deleted')
    search_fields = ('service_name', 'username', 'vo_name', 'approver')

    @admin.display(description=gettext_lazy('删除'))
    def show_deleted(self, obj):
        if obj.deleted:
            return 'Yes'

        return 'No'
