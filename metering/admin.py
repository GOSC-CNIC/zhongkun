from django.contrib import admin

from .models import (
    MeteringServer, MeteringDisk, MeteringObjectStorage, DailyStatementServer, DailyStatementObjectStorage,
    DailyStatementDisk, MeteringMonitorWebsite
)


@admin.register(MeteringServer)
class MeteringServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'cpu_hours', 'ram_hours', 'disk_hours', 'public_ip_hours',
                    'snapshot_hours', 'upstream', 'downstream', 'pay_type', 'service',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'server_id', 'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringDisk)
class MeteringDiskAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'size_hours', 'snapshot_hours', 'pay_type', 'service',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'disk_id', 'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringObjectStorage)
class MeteringObjectStorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'storage_byte', 'storage', 'downstream', 'replication', 'get_request',
                    'put_request', 'billed_network_flow', 'unbilled_network_flow', 'service', 'bucket_name', 'storage_bucket_id',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    list_filter = ('service',)
    search_fields = ('bucket_name', 'user_id')
    list_select_related = ('service',)


@admin.register(MeteringMonitorWebsite)
class MeteringMonitorWebsiteAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'website_id', 'website_name', 'hours', 'detection_count', 'tamper_resistant_count',
                    'security_count', 'original_amount', 'trade_amount', 'daily_statement_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    search_fields = ('user_id', 'username', 'website_id')


@admin.register(DailyStatementServer)
class DailyStatementServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'payment_status')
    search_fields = ('username', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(DailyStatementObjectStorage)
class DailyStatementObjectStorageAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    list_filter = ('payment_status',)
    search_fields = ('username',)
    list_select_related = ('service',)


@admin.register(DailyStatementDisk)
class DailyStatementDiskAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'payment_status')
    search_fields = ('username', 'user_id', 'vo_id')
    list_select_related = ('service',)
