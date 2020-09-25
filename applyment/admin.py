from django.contrib import admin

from .models import ApplyService, ApplyQuota


@admin.register(ApplyService)
class ApplyServiceAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'data_center', 'name', 'service_type', 'status', 'user', 'creation_time', 'approve_time')

    list_filter = ('data_center',)


@admin.register(ApplyQuota)
class ApplyQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpu', 'ram', 'disk_size', 'public_ip', 'private_ip', 'status', 'user', 'creation_time', 'approve_time')

