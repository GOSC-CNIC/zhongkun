from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _
from django.contrib import messages
from django.db import transaction

from servers.models import Server, Disk
from utils.model import NoDeleteSelectModelAdmin
from .models import (
    ServiceConfig, DataCenter, ServicePrivateQuota,
    ServiceShareQuota, ApplyVmService, ApplyOrganization, Contacts,
    OrgDataCenter
)
from . import forms


@admin.register(ServiceConfig)
class ServiceConfigAdmin(NoDeleteSelectModelAdmin):
    form = forms.VmsProviderForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'org_data_center', 'organization_name', 'sort_weight', 'region_id', 'service_type',
                    'endpoint_url', 'username',
                    'password', 'add_time', 'status', 'need_vpn', 'disk_available', 'vpn_endpoint_url', 'vpn_password',
                    'pay_app_service_id', 'longitude', 'latitude', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['service_type', 'disk_available']
    list_select_related = ('org_data_center', 'org_data_center__organization')
    raw_id_fields = ('org_data_center',)
    list_editable = ('sort_weight',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', 'vpn_password')
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks', 'sort_weight')}),
        (_('服务配置信息'), {
            'fields': ('data_center', 'name', 'name_en', 'service_type', 'cloud_type', 'status', 'endpoint_url',
                       'api_version', 'region_id', 'disk_available', 'username', 'password', 'change_password')
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

    @admin.display(description=gettext_lazy("机构"))
    def organization_name(self, obj):
        if not obj.org_data_center or not obj.org_data_center.organization:
            return ''

        return obj.org_data_center.organization.name

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj: ServiceConfig, form, change):
        if change:
            super().save_model(request=request, obj=obj, form=form, change=change)
            try:
                obj.sync_to_pay_app_service()
            except Exception as exc:
                self.message_user(request, _("更新服务单元对应的结算服务单元错误") + str(exc), level=messages.ERROR)
        else:   # add
            with transaction.atomic():
                super().save_model(request=request, obj=obj, form=form, change=change)
                obj.check_or_register_pay_app_service()


@admin.register(DataCenter)
class DataCenterAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'abbreviation', 'status', 'sort_weight',
                    'creation_time', 'longitude', 'latitude', 'desc')
    list_editable = ('sort_weight', )
    search_fields = ('name', 'name_en', 'abbreviation')
    filter_horizontal = ('contacts',)


@admin.register(OrgDataCenter)
class OrgDataCenterAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'organization', 'sort_weight', 'longitude', 'latitude', 'creation_time',
                    'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                    'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url',
                    )
    search_fields = ['name', 'name_en', 'thanos_endpoint_url', 'loki_endpoint_url', 'remark']
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)
    list_editable = ('sort_weight',)
    filter_horizontal = ('users',)
    fieldsets = (
        (_('数据中心基础信息'), {
            'fields': (
                'name', 'name_en', 'organization', 'sort_weight', 'longitude', 'latitude', 'remark',
                'users'
            )
        }),
        (_('Thanos服务信息'), {
            'fields': (
                'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark'
            )
        }),
        (_('Loki服务信息'), {
            'fields': (
                'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'
            )
        }),
    )


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
            disk_stat = Disk.count_private_quota_used(q.service_id)

            with transaction.atomic():
                quota = ServicePrivateQuota.objects.select_for_update().get(id=q.id)
                update_fields = []
                vcpu_used_count = r.get('vcpu_used_count', None)
                if isinstance(vcpu_used_count, int) and quota.vcpu_used != vcpu_used_count:
                    quota.vcpu_used = vcpu_used_count
                    update_fields.append('vcpu_used')

                ram_used_count = r.get('ram_used_count', None)
                if isinstance(ram_used_count, int) and quota.ram_used_gib != ram_used_count:
                    quota.ram_used_gib = ram_used_count
                    update_fields.append('ram_used')

                public_ip_count = r.get('public_ip_count', None)
                if isinstance(public_ip_count, int) and quota.public_ip_used != public_ip_count:
                    quota.public_ip_used = public_ip_count
                    update_fields.append('public_ip_used')

                private_ip_used = r.get('private_ip_count', None)
                if isinstance(private_ip_used, int) and quota.private_ip_used != private_ip_used:
                    quota.private_ip_used = private_ip_used
                    update_fields.append('private_ip_used')

                # 云硬盘
                disk_size_used_count = disk_stat.get('disk_used_count', None)
                if isinstance(disk_size_used_count, int) and quota.disk_size_used != disk_size_used_count:
                    quota.disk_size_used = disk_size_used_count
                    update_fields.append('disk_size_used')

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
                if isinstance(ram_used_count, int) and quota.ram_used_gib != ram_used_count:
                    quota.ram_used_gib = ram_used_count
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


@admin.register(Contacts)
class ContactsAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'telephone', 'email', 'address', 'creation_time', 'remarks')
