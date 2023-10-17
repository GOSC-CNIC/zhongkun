from django.contrib import admin
from django.utils.translation import gettext_lazy

from .models import (
    IPAMUserRole, OrgVirtualObject, ASN, IPv4Address, IPv4Range, IPv4RangeRecord
)


@admin.register(IPAMUserRole)
class IPAMUserRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_admin', 'is_readonly', 'creation_time', 'update_time')
    list_select_related = ('user',)
    raw_id_fields = ('user',)
    search_fields = ('user_username',)
    filter_horizontal = ('organizations',)


@admin.register(OrgVirtualObject)
class OrgVirtualObjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'creation_time', 'remark')
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)
    search_fields = ('name', 'organization__name', 'remark')


@admin.register(ASN)
class ASNAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'name', 'creation_time')
    search_fields = ('name',)


@admin.register(IPv4Address)
class IPv4AddressAdmin(admin.ModelAdmin):
    list_display = ('id', 'ip_address', 'display_ip_addr', 'ip_range', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    list_select_related = ('ip_range',)
    raw_id_fields = ('ip_range',)
    search_fields = ('admin_remark', 'remark', 'ip_address')

    @staticmethod
    @admin.display(description=gettext_lazy('IP地址'))
    def display_ip_addr(obj: IPv4Address):
        return obj.ip_address_str()


@admin.register(IPv4Range)
class IPv4RangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'start_address', 'end_address', 'mask_len', 'display_ip_range', 'asn', 'status',
                    'org_virt_obj', 'assigned_time', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    list_select_related = ('asn', 'org_virt_obj')
    list_filter = ('status',)
    search_fields = ('name', 'admin_remark', 'remark')
    raw_id_fields = ('org_virt_obj',)

    @staticmethod
    @admin.display(description=gettext_lazy('地址段易读显示'))
    def display_ip_range(obj: IPv4Range):
        return obj.ip_range_display()


@admin.register(IPv4RangeRecord)
class IPv4RangeRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'start_address', 'end_address', 'mask_len', 'display_ip_range',
                    'org_virt_obj', 'creation_time', 'user', 'remark')
    list_select_related = ('user', 'org_virt_obj')
    raw_id_fields = ('org_virt_obj', 'user')
    search_fields = ('name', 'remark')

    @staticmethod
    def display_ip_range(obj: IPv4RangeRecord):
        return obj.ip_range_display()
