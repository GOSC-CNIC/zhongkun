from django.contrib import admin

from .models import Order, Resource


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_type', 'status', 'total_amount', 'pay_amount', 'service_name',
                    'resource_type', 'period', 'pay_type', 'payment_time',
                    'creation_time', 'owner_type', 'username', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'resource_type', 'pay_type', 'status', 'order_type')
    search_fields = ('id', 'username', 'vo_name')


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_id', 'resource_type', 'instance_id', 'instance_status', 'creation_time')
    list_display_links = ('id',)
    list_filter = ('resource_type', 'instance_status')
    search_fields = ('order_id', )
    raw_id_fields = ('order',)

