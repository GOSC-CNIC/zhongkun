from django.contrib import admin

from .models import Bill, PaymentHistory, UserPointAccount, VoPointAccount


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'status', 'amounts', 'creation_time', 'resource_type',
                    'service_id', 'instance_id', 'order_id', 'owner_type', 'user_id', 'vo_id')
    list_display_links = ('id',)
    list_filter = ('type', 'resource_type', 'owner_type')
    search_fields = ('id', 'order_id', 'instance_id', 'user_id', 'vo_id', 'service_id')


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'amounts', 'before_payment', 'after_payment', 'payment_time',
                    'payer_type', 'payer_id', 'payer_name')
    list_display_links = ('id',)
    list_filter = ('type', 'payer_type')
    search_fields = ('id', 'payer_id', 'payer_name')
    raw_id_fields = ('bill',)


@admin.register(UserPointAccount)
class UserPointAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'user',)
    list_display_links = ('id',)
    list_select_related = ('user',)


@admin.register(VoPointAccount)
class VoPointAccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'balance', 'vo',)
    list_display_links = ('id',)
    list_select_related = ('vo',)
