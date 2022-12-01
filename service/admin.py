from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _
from django.contrib import messages
from django.db import transaction

from servers.models import Server
from utils.model import NoDeleteSelectModelAdmin
from .models import (
    ServiceConfig, DataCenter, ServicePrivateQuota,
    ServiceShareQuota, ApplyVmService, ApplyOrganization
)
from . import forms


@admin.register(ServiceConfig)
class ServiceConfigAdmin(NoDeleteSelectModelAdmin):
    form = forms.VmsProviderForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'data_center', 'region_id', 'service_type', 'endpoint_url', 'username',
                    'password', 'add_time', 'status', 'need_vpn', 'vpn_endpoint_url', 'vpn_password',
                    'longitude', 'latitude', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['data_center', 'service_type']
    list_select_related = ('data_center',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', 'vpn_password')
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks',)}),
        (_('服务配置信息'), {
            'fields': ('data_center', 'name', 'name_en', 'service_type', 'cloud_type', 'status', 'endpoint_url',
                       'api_version', 'region_id', 'username', 'password', 'change_password')
        }),
        (_('VPN配置信息'), {
            'fields': ('need_vpn', 'vpn_endpoint_url', 'vpn_api_version', 'vpn_username',
                       'vpn_password', 'change_vpn_password')
        }),
        (_('支付结算信息'), {'fields': ('pay_app_service_id',)}),
        (_('其他配置信息'), {'fields': ('extra', 'logo_url', 'longitude', 'latitude')}),
        (_('服务管理员'), {'fields': ('users', )}),
        (_('联系人信息'), {
            'fields': ('contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address')
        }),
    )

    actions = ['encrypt_password', 'encrypt_vpn_password']

    @admin.action(description=gettext_lazy("加密用户密码"))
    def encrypt_password(self, request, queryset):
        """
        加密密码
        """
        count = 0
        for service in queryset:
            if service.raw_password() is None:
                service.set_password(service.password)
                service.save(update_fields=['password'])
                count += 1

        if count > 0:
            self.message_user(request, _("加密更新数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, _("没有加密更新任何数据记录"), level=messages.SUCCESS)

    @admin.action(description=gettext_lazy("加密vpn用户密码"))
    def encrypt_vpn_password(self, request, queryset):
        """
        加密密码
        """
        count = 0
        for service in queryset:
            if service.raw_vpn_password() is None:
                service.set_vpn_password(service.vpn_password)
                service.save(update_fields=['vpn_password'])
                count += 1

        if count > 0:
            self.message_user(request, _("加密更新数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, _("没有加密更新任何数据记录"), level=messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DataCenter)
class DataCenterAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'abbreviation', 'status', 'creation_time', 'longitude', 'latitude', 'desc')


@admin.register(ServicePrivateQuota)
class ServicePrivateQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__data_center', 'service')
    actions = ['quota_used_update']

    @admin.action(description=gettext_lazy("已用配额统计更新"))
    def quota_used_update(self, request, queryset):
        failed_count = 0
        for q in queryset:
            r = Server.count_private_quota_used(q.service_id)

            with transaction.atomic():
                quota = ServicePrivateQuota.objects.select_for_update().get(id=q.id)
                update_fields = []
                vcpu_used_count = r.get('vcpu_used_count', None)
                if isinstance(vcpu_used_count, int) and quota.vcpu_used != vcpu_used_count:
                    quota.vcpu_used = vcpu_used_count
                    update_fields.append('vcpu_used')

                ram_used_count = r.get('ram_used_count', None)
                if isinstance(ram_used_count, int) and quota.ram_used != ram_used_count:
                    quota.ram_used = ram_used_count
                    update_fields.append('ram_used')

                public_ip_count = r.get('public_ip_count', None)
                if isinstance(public_ip_count, int) and quota.public_ip_used != public_ip_count:
                    quota.public_ip_used = public_ip_count
                    update_fields.append('public_ip_used')

                private_ip_used = r.get('private_ip_count', None)
                if isinstance(private_ip_used, int) and quota.private_ip_used != private_ip_used:
                    quota.private_ip_used = private_ip_used
                    update_fields.append('private_ip_used')

                if update_fields:
                    try:
                        quota.save(update_fields=update_fields)
                    except Exception as e:
                        failed_count += 1

        if failed_count != 0:
            self.message_user(request, _("统计更新已用配额失败") + f'({failed_count})', level=messages.ERROR)
        else:
            self.message_user(request, _("统计更新已用配额成功"), level=messages.SUCCESS)


@admin.register(ServiceShareQuota)
class ServiceShareQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__data_center', 'service')
    actions = ['quota_used_update']

    @admin.action(description=gettext_lazy("已用配额统计更新"))
    def quota_used_update(self, request, queryset):
        failed_count = 0
        for q in queryset:
            r = Server.count_share_quota_used(q.service_id)

            with transaction.atomic():
                quota = ServiceShareQuota.objects.select_for_update().get(id=q.id)
                update_fields = []
                vcpu_used_count = r.get('vcpu_used_count', None)
                if isinstance(vcpu_used_count, int) and quota.vcpu_used != vcpu_used_count:
                    quota.vcpu_used = vcpu_used_count
                    update_fields.append('vcpu_used')

                ram_used_count = r.get('ram_used_count', None)
                if isinstance(ram_used_count, int) and quota.ram_used != ram_used_count:
                    quota.ram_used = ram_used_count
                    update_fields.append('ram_used')

                public_ip_count = r.get('public_ip_count', None)
                if isinstance(public_ip_count, int) and quota.public_ip_used != public_ip_count:
                    quota.public_ip_used = public_ip_count
                    update_fields.append('public_ip_used')

                private_ip_used = r.get('private_ip_count', None)
                if isinstance(private_ip_used, int) and quota.private_ip_used != private_ip_used:
                    quota.private_ip_used = private_ip_used
                    update_fields.append('private_ip_used')

                if update_fields:
                    try:
                        quota.save(update_fields=update_fields)
                    except Exception as e:
                        failed_count += 1

        if failed_count != 0:
            self.message_user(request, _("统计更新已用配额失败") + f'({failed_count})', level=messages.ERROR)
        else:
            self.message_user(request, _("统计更新已用配额成功"), level=messages.SUCCESS)


@admin.register(ApplyVmService)
class ApplyServiceAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'organization', 'name', 'name_en', 'service_type', 'status', 'user',
                    'creation_time', 'approve_time')

    list_filter = ('organization',)


@admin.register(ApplyOrganization)
class ApplyOrganizationAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'abbreviation', 'status', 'user', 'deleted', 'creation_time', 'desc')
