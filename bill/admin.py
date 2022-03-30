from django.contrib import admin

from .models import PaymentHistory, UserPointAccount, VoPointAccount


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
    list_display = ('id', 'balance', 'vo',)
    list_display_links = ('id',)
    list_select_related = ('vo',)
    readonly_fields = ('balance',)
