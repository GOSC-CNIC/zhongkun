from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _

from .models import ServiceConfig, DataCenter, DataCenterPrivateQuota, DataCenterShareQuota, UserQuota


@admin.register(ServiceConfig)
class ServiceConfigAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'data_center', 'region_id', 'service_type', 'endpoint_url', 'username', 'password',
                    'add_time', 'status', 'need_vpn', 'vpn_endpoint_url', 'remarks')
    search_fields = ['name', 'endpoint_url', 'remarks']
    list_filter = ['data_center', 'service_type']
    list_select_related = ('data_center',)


@admin.register(DataCenter)
class DataCenterAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'status', 'desc')

    filter_horizontal = ('users',)


@admin.register(DataCenterPrivateQuota)
class DataCenterPrivateQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'data_center', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable')
    list_select_related = ('data_center',)
    list_filter = ('data_center',)


@admin.register(DataCenterShareQuota)
class DataCenterShareQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'data_center', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable')
    list_select_related = ('data_center',)
    list_filter = ('data_center',)


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'tag', 'user', 'show_deleted', 'expiration_time', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used',
                    'disk_size_total', 'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used')
    list_select_related = ('user',)
    search_fields = ['user__username']
    # list_filter = ('show_deleted',)

    def show_deleted(self, obj):
        if obj.deleted:
            return _("已删除")

        return _('否')

    show_deleted.short_description = gettext_lazy('删除')
