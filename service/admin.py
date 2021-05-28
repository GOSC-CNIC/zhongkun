from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _
from django.contrib import messages
from django.db import transaction

from servers.models import Server, ServerArchive
from .models import (ServiceConfig, DataCenter, ServicePrivateQuota,
                     ServiceShareQuota, UserQuota, ApplyVmService)


@admin.register(ServiceConfig)
class ServiceConfigAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'data_center', 'region_id', 'service_type', 'endpoint_url', 'username', 'password',
                    'add_time', 'status', 'need_vpn', 'vpn_endpoint_url', 'vpn_password', 'remarks')
    search_fields = ['name', 'endpoint_url', 'remarks']
    list_filter = ['data_center', 'service_type']
    list_select_related = ('data_center',)

    filter_horizontal = ('users',)
    readonly_fields = ('password',)

    actions = ['encrypt_password', 'encrypt_vpn_password']

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

    encrypt_password.short_description = gettext_lazy("加密用户密码")

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

    encrypt_vpn_password.short_description = gettext_lazy("加密vpn用户密码")


@admin.register(DataCenter)
class DataCenterAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'status', 'desc')


@admin.register(ServicePrivateQuota)
class ServicePrivateQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__data_center', 'service')
    actions = ['quota_used_update']

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

    quota_used_update.short_description = gettext_lazy("已用配额统计更新")


@admin.register(ServiceShareQuota)
class ServiceShareQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__data_center', 'service')
    actions = ['quota_used_update']

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

    quota_used_update.short_description = gettext_lazy("已用配额统计更新")


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'tag', 'user', 'service', 'show_deleted', 'expiration_time', 'duration_days',
                    'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used')
    list_select_related = ('user', 'service')
    search_fields = ['user__username']
    actions = ['quota_used_update']
    list_filter = ('service', 'tag')

    def show_deleted(self, obj):
        if obj.deleted:
            return _("已删除")

        return _('否')

    show_deleted.short_description = gettext_lazy('删除')

    def quota_used_update(self, request, queryset):
        failed_count = 0
        for q in queryset:
            # 虚拟服务器和已归档服务器总的已用资源配额
            r = Server.count_user_quota_used(q)
            ar = ServerArchive.count_user_quota_used(q)
            vcpu_used_count = r.get('vcpu_used_count') + ar.get('vcpu_used_count')
            ram_used_count = r.get('ram_used_count') + ar.get('ram_used_count')
            public_ip_count = r.get('public_ip_count') + ar.get('public_ip_count')
            private_ip_used = r.get('private_ip_count') + ar.get('private_ip_count')

            with transaction.atomic():
                quota = UserQuota.objects.select_for_update().get(id=q.id)
                update_fields = []
                if isinstance(vcpu_used_count, int) and quota.vcpu_used != vcpu_used_count:
                    quota.vcpu_used = vcpu_used_count
                    update_fields.append('vcpu_used')

                if isinstance(ram_used_count, int) and quota.ram_used != ram_used_count:
                    quota.ram_used = ram_used_count
                    update_fields.append('ram_used')

                if isinstance(public_ip_count, int) and quota.public_ip_used != public_ip_count:
                    quota.public_ip_used = public_ip_count
                    update_fields.append('public_ip_used')

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

    quota_used_update.short_description = gettext_lazy("已用配额统计更新")


@admin.register(ApplyVmService)
class ApplyServiceAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'data_center', 'name', 'service_type', 'status', 'user', 'creation_time', 'approve_time')

    list_filter = ('data_center',)
