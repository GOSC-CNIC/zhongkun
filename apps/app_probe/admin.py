from django.contrib import admin

from apps.app_probe.models import ProbeDetails, ProbeMonitorWebsite
from utils.model import BaseModelAdmin


# Register your models here.

@admin.register(ProbeDetails)
class ProbeDetailsAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'probe_type', 'version')


@admin.register(ProbeMonitorWebsite)
class ProbeMonitorWebsiteAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'uri', 'url_hash', 'is_tamper_resistant', 'creation', 'tls_time', 'connect_time', 'processing_time', 'resolve_time', 'transfer_time', 'status')