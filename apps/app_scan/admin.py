from django.contrib import admin, messages
from django.utils.translation import gettext
from django.db import transaction

from utils.model import BaseModelAdmin
from .models import VtScanService, VtScanner, VtReport, VtTask


@admin.register(VtScanService)
class VtScanServiceAdmin(BaseModelAdmin):
    list_display = ['name', 'status', 'pay_app_service_id']

    def save_model(self, request, obj: VtScanService, form, change):
        if change:
            super().save_model(request=request, obj=obj, form=form, change=change)
            try:
                obj.sync_to_pay_app_service()
            except Exception as exc:
                self.message_user(request, gettext("更新服务单元对应的结算服务单元错误") + str(exc), level=messages.ERROR)
        else:   # add
            with transaction.atomic():
                super().save_model(request=request, obj=obj, form=form, change=change)
                obj.check_or_register_pay_app_service()

    def has_delete_permission(self, request, obj=None):
        return False


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
    list_display = ['id', 'name', 'type', 'task_status', 'target', 'create_time', 'user', 'scanner', 'running_status',
                    'finish_time', 'report', 'remark']
    list_select_related = ('scanner', 'report', 'user')
    list_filter = ('type', 'task_status', 'running_status')
    search_fields = ('name', 'remark', 'user__username')
    raw_id_fields = ('user', 'scanner')
