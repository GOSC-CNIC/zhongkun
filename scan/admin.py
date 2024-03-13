from django.contrib import admin
from utils.model import BaseModelAdmin

from .models import VtScanService, VtScanner, VtReport, VtTask


@admin.register(VtScanService)
class VtScanServiceAdmin(BaseModelAdmin):
    list_display = ['name', 'status', 'host_scan_price', 'web_scan_price', 'pay_app_service_id']


@admin.register(VtScanner)
class VtScannerAdmin(BaseModelAdmin):
    list_display = ['name', 'type', 'engine', 'ipaddr', 'port', 'status', 'key', 'max_concurrency']
    list_filter = ('type', 'engine', 'status')


@admin.register(VtReport)
class VtReportAdmin(BaseModelAdmin):
    list_display = ['filename', 'type', 'create_time']
    search_fields = ('filename',)


@admin.register(VtTask)
class VtTaskAdmin(BaseModelAdmin):
    list_display = ['id', 'name', 'type', 'task_status', 'create_time', 'user', 'scanner', 'running_status',
                    'finish_time', 'report', 'pay_amount', 'payment_history_id', 'remark']
    list_select_related = ('scanner', 'report', 'user')
    list_filter = ('type', 'task_status', 'running_status')
    search_fields = ('name', 'remark', 'user__username')
    raw_id_fields = ('user', 'scanner')
