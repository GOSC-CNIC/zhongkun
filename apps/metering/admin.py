from django.contrib import admin

from utils.model import BaseModelAdmin
from .models import (
    MeteringServer, MeteringDisk, MeteringObjectStorage, DailyStatementServer, DailyStatementObjectStorage,
    DailyStatementDisk, MeteringMonitorWebsite, DailyStatementMonitorWebsite
)


@admin.register(MeteringServer)
class MeteringServerAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'cpu_hours', 'ram_hours', 'disk_hours', 'public_ip_hours',
                    'snapshot_hours', 'upstream', 'downstream', 'pay_type', 'service',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'server_id', 'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringDisk)
class MeteringDiskAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'size_hours', 'snapshot_hours', 'pay_type', 'service',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'disk_id', 'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type',)
    search_fields = ('server_id', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(MeteringObjectStorage)
class MeteringObjectStorageAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'storage_byte', 'storage', 'downstream', 'replication', 'get_request',
                    'put_request', 'billed_network_flow', 'unbilled_network_flow', 'service', 'bucket_name', 'storage_bucket_id',
                    'original_amount', 'trade_amount', 'daily_statement_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    list_filter = ('service',)
    search_fields = ('bucket_name', 'user_id')
    list_select_related = ('service',)


@admin.register(MeteringMonitorWebsite)
class MeteringMonitorWebsiteAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'website_id', 'website_name', 'hours', 'detection_count', 'tamper_resistant_count',
                    'security_count', 'original_amount', 'trade_amount', 'daily_statement_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    search_fields = ('user_id', 'username', 'website_id')


@admin.register(DailyStatementServer)
class DailyStatementServerAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'payment_status')
    search_fields = ('username', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(DailyStatementObjectStorage)
class DailyStatementObjectStorageAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    list_filter = ('payment_status',)
    search_fields = ('username',)
    list_select_related = ('service',)


@admin.register(DailyStatementDisk)
class DailyStatementDiskAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'service',
                    'original_amount', 'payable_amount', 'trade_amount', 'payment_status', 'payment_history_id',
                    'creation_time', 'owner_type', 'user_id', 'username', 'vo_id', 'vo_name')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'payment_status')
    search_fields = ('username', 'user_id', 'vo_id')
    list_select_related = ('service',)


@admin.register(DailyStatementMonitorWebsite)
class DailyStMonitorSiteAdmin(BaseModelAdmin):
    list_display = ('id', 'date', 'original_amount', 'payable_amount', 'trade_amount', 'payment_status',
                    'payment_history_id', 'creation_time', 'user_id', 'username')
    list_display_links = ('id',)
    list_filter = ('payment_status',)
    search_fields = ('username', 'user_id')
