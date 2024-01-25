from django.contrib import admin

from utils.model import NoDeleteSelectModelAdmin
from .models import MonthlyReport, BucketMonthlyReport, BucketStatsMonthly, ArrearServer, ArrearBucket


@admin.register(MonthlyReport)
class MonthlyReportAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'report_date', 'is_reported', 'owner_type', 'user', 'vo', 'server_count',
                    'server_original_amount', 'server_payable_amount', 'server_postpaid_amount',
                    'server_prepaid_amount', 'server_cpu_days', 'server_ram_days', 'server_disk_days',
                    'server_ip_days', 'bucket_count', 'storage_days', 'storage_original_amount',
                    'storage_payable_amount', 'storage_postpaid_amount',
                    'disk_count', 'disk_size_days', 'disk_original_amount', 'disk_payable_amount',
                    'disk_postpaid_amount', 'disk_prepaid_amount',
                    'site_count', 'site_days', 'site_tamper_days', 'site_original_amount', 'site_payable_amount',
                    'site_paid_amount', 'notice_time')
    search_fields = ['id', 'user__username', 'vo__name']
    list_filter = ['is_reported', 'owner_type']
    raw_id_fields = ('user', 'vo')
    list_select_related = ('user', 'vo')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(BucketMonthlyReport)
class BucketMonthlyReportAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'report_date', 'username', 'bucket_name', 'creation_time',
                    'storage_days', 'original_amount', 'payable_amount')
    search_fields = ['id', 'username', 'bucket_id']
    raw_id_fields = ('user',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(BucketStatsMonthly)
class BucketStatsMonthlyAdmin(admin.ModelAdmin):
    list_display = ('id', 'bucket_id', 'bucket_name', 'service', 'size_byte', 'increment_byte', 'object_count',
                    'original_amount', 'increment_amount', 'user', 'date', 'creation_time')
    list_select_related = ('service', 'user')
    raw_id_fields = ('user',)
    search_fields = ['bucket_id', 'bucket_name']
    list_filter = ['service', ]

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArrearServer)
class ArrearServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'server_id', 'ipv4', 'vcpus', 'ram', 'image', 'service_name',
                    'server_creation', 'server_expire', 'pay_type', 'user_id', 'username',
                    'vo_id', 'vo_name', 'owner_type', 'balance_amount', 'date', 'creation_time', 'remarks')
    # list_select_related = ('service',)
    search_fields = ['server_id', 'ipv4', 'user_id', 'username']
    list_filter = ['service', 'pay_type', 'owner_type']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArrearBucket)
class ArrearBucketAdmin(admin.ModelAdmin):
    list_display = ('id', 'bucket_id', 'bucket_name', 'service_name', 'size_byte', 'object_count',
                    'bucket_creation', 'user_id', 'username', 'balance_amount', 'date', 'creation_time')
    # list_select_related = ('service',)
    search_fields = ['bucket_id', 'bucket_name', 'user_id', 'username']
    list_filter = ['service', ]

    def has_delete_permission(self, request, obj=None):
        return False
