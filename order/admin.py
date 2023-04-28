from django.contrib import admin

from .models import Order, Resource, Price


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_type', 'status', 'total_amount', 'payable_amount', 'pay_amount',
                    'balance_amount', 'coupon_amount', 'service_name',
                    'resource_type', 'period', 'pay_type', 'payment_time',
                    'creation_time', 'trading_status', 'completion_time', 'deleted',
                    'owner_type', 'username', 'vo_name', 'cancelled_time', 'app_service_id')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'resource_type', 'pay_type', 'status', 'order_type', 'trading_status', 'deleted')
    search_fields = ('id', 'username', 'vo_name')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_id', 'resource_type', 'instance_id', 'instance_status', 'delivered_time',
                    'desc', 'instance_remark', 'creation_time')
    list_display_links = ('id',)
    list_filter = ('resource_type', 'instance_status')
    search_fields = ('order__id', 'instance_id')
    raw_id_fields = ('order',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('id', 'vm_ram', 'vm_cpu', 'vm_pub_ip', 'vm_disk', 'vm_disk_snap', 'vm_upstream',
                    'vm_downstream', 'disk_size', 'disk_snap', 'obj_size', 'obj_upstream', 'obj_downstream',
                    'obj_replication', 'obj_get_request', 'obj_put_request', 'prepaid_discount')
    list_display_links = ('id',)
