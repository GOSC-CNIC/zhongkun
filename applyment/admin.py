from django.contrib import admin

from .models import ApplyQuota


@admin.register(ApplyQuota)
class ApplyQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpu', 'ram', 'disk_size', 'public_ip', 'private_ip', 'status', 'user', 'creation_time', 'approve_time')

