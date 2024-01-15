from django.contrib import admin, messages
from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.html import format_html
from django.db import transaction
from django import forms

from utils.model import NoDeleteSelectModelAdmin, PayType
from service.forms import VmsProviderForm
from .models import (
    Server, Flavor, ServerArchive, Disk, ResourceActionLog, DiskChangeLog,
    ServiceConfig, ServicePrivateQuota, ServiceShareQuota,
)


class ServerAdminForm(forms.ModelForm):
    change_password = forms.CharField(
        label=_('更改默认登录密码输入'), required=False, min_length=3, max_length=32,
        help_text=_('如果要更改默认登录密码，请在此输入新密码, 不修改请保持为空'))

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        if change_password:
            self.instance.raw_default_password = change_password

        return super().save(commit=commit)


@admin.register(Server)
class ServerAdmin(NoDeleteSelectModelAdmin):
    form = ServerAdminForm
    list_display_links = ('id',)
    list_display = ('id', 'service', 'azone_id', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                    'creation_time', 'start_time', 'user', 'task_status', 'center_quota',
                    'pay_type', 'classification', 'vo', 'lock', 'situation', 'situation_time',
                    'default_user', 'show_default_password', 'expiration_time', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['service__org_data_center', 'service', 'classification']
    raw_id_fields = ('user', )
    list_select_related = ('service', 'user', 'vo')
    readonly_fields = ['default_password']

    fieldsets = [
        (_('基础信息'), {'fields': ('service', 'azone_id', 'instance_id', 'remarks', 'center_quota')}),
        (_('配置信息'), {'fields': (
            'vcpus', 'ram', 'disk_size', 'ipv4', 'image', 'img_sys_type',
            'img_sys_arch', 'img_release', 'img_release_version',)}),
        (_('默认登录密码'), {'fields': ('default_user', 'default_password', 'change_password')}),
        (_('创建和归属信息'), {'fields': ('creation_time', 'task_status', 'classification', 'user', 'vo')}),
        (_('计量和管控信息'), {'fields': (
            'pay_type', 'start_time', 'expiration_time', 'lock', 'situation', 'situation_time')}),
    ]

    @admin.display(
        description=_('默认登录密码')
    )
    def show_default_password(self, obj):
        return obj.raw_default_password

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(gettext('不允许从后台删除。'))

    def save_model(self, request, obj, form, change):
        # 按量付费，没有过期时间
        if obj.pay_type == PayType.POSTPAID.value:
            obj.expiration_time = None

        super().save_model(request=request, obj=obj, form=form, change=change)


@admin.register(ServerArchive)
class ServerArchiveAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                    'creation_time', 'user', 'task_status', 'pay_type', 'classification', 'vo',
                    'center_quota',
                    'start_time', 'deleted_time', 'archive_user', 'archive_type', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['archive_type', 'service', 'classification']
    raw_id_fields = ('user',)
    list_select_related = ('service', 'user', 'archive_user', 'vo')
    show_full_result_count = False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'service', 'creation_time')
    ordering = ('vcpus', 'ram')
    list_filter = ['service']


@admin.register(Disk)
class DiskAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'azone_id', 'azone_name', 'size', 'instance_id', 'quota_type',
                    'creation_time', 'task_status', 'expiration_time', 'start_time', 'pay_type',
                    'classification', 'user', 'vo', 'lock', 'show_deleted', 'deleted_time', 'deleted_user',
                    'server', 'mountpoint', 'attached_time', 'detached_time', 'remarks')
    search_fields = ['id', 'instance_id', 'remarks', 'user__username']
    list_filter = ['service__org_data_center', 'service', 'classification', 'deleted']
    raw_id_fields = ('user', 'vo', 'server')
    list_select_related = ('service', 'user', 'vo')
    readonly_fields = ['deleted_user']

    fieldsets = [
        (_('基础信息'), {'fields': ('service', 'azone_id', 'azone_name', 'size', 'instance_id', 'remarks', 'quota_type')}),
        (_('创建和归属信息'), {'fields': ('creation_time', 'task_status', 'classification', 'user', 'vo')}),
        (_('计量信息'), {'fields': ('pay_type', 'start_time', 'expiration_time')}),
        (_('挂载信息'), {'fields': ('server', 'mountpoint', 'attached_time', 'detached_time')}),
        (_('锁、删除状态'), {'fields': ('lock', 'deleted', 'deleted_time', 'deleted_user')}),
    ]

    @admin.display(
        description=_('删除状态')
    )
    def show_deleted(self, obj):
        if obj.deleted:
            return gettext('已删除')

        return gettext('正常')

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(gettext('不允许从后台删除。'))


@admin.register(ResourceActionLog)
class ResourceActionLogAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'action_time', 'username', 'action_flag', 'resource_type', 'resource_repr',
                    'owner_name', 'owner_type')
    search_fields = ['user_id', 'username', 'resource_id', 'owner_id']
    list_filter = ['action_flag', 'resource_type']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DiskChangeLog)
class DiskChangeLogAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'log_type', 'change_time', 'change_user', 'disk_id', 'service', 'azone_id', 'azone_name',
                    'size', 'instance_id', 'quota_type', 'creation_time', 'task_status',
                    'expiration_time', 'start_time', 'pay_type',
                    'classification', 'user', 'vo', 'remarks')
    search_fields = ['disk_id', 'instance_id', 'remarks', 'user__username', 'change_user']
    list_filter = ['log_type', 'service', 'classification']
    raw_id_fields = ('user', 'vo',)
    list_select_related = ('service', 'user', 'vo')
    readonly_fields = ['change_user']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


class ServiceOrgFilter(SimpleListFilter):
    title = _("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        r = ServiceConfig.objects.select_related('org_data_center__organization').order_by('sort_weight').values_list(
            'org_data_center__organization_id', 'org_data_center__organization__name'
        )
        d = {i[0]: i[1] for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(org_data_center__organization_id=org_id)


@admin.register(ServiceConfig)
class ServiceConfigAdmin(NoDeleteSelectModelAdmin):
    form = VmsProviderForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'org_data_center', 'organization_name', 'sort_weight',
                    'only_admin_visible', 'region_id', 'service_type', 'endpoint_url', 'username',
                    'password', 'raw_password', 'add_time', 'status', 'need_vpn', 'disk_available',
                    'vpn_endpoint_url', 'vpn_password',
                    'pay_app_service_id', 'longitude', 'latitude', 'remarks', 'monitor_task_id')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['service_type', 'disk_available', ServiceOrgFilter]
    list_select_related = ('org_data_center', 'org_data_center__organization')
    raw_id_fields = ('org_data_center',)
    list_editable = ('sort_weight',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', 'vpn_password', 'monitor_task_id')
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks', 'sort_weight', 'only_admin_visible')}),
        (_('服务配置信息'), {
            'fields': ('org_data_center', 'name', 'name_en', 'service_type', 'cloud_type', 'status', 'endpoint_url',
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
        (_('监控任务'), {'fields': ('monitor_task_id', 'delete_monitor_task')}),
    )

    actions = ['encrypt_password', 'encrypt_vpn_password']

    @admin.action(description=_("加密用户密码"))
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

    @admin.action(description=_("加密vpn用户密码"))
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

    @admin.display(description=_("机构"))
    def organization_name(self, obj):
        if not obj.org_data_center or not obj.org_data_center.organization:
            return ''

        return obj.org_data_center.organization.name

    @admin.display(description=_("原始密码"))
    def raw_password(self, obj):
        passwd = obj.raw_password()
        if not passwd:
            return passwd

        return format_html(f'<div title="{passwd}">******</div>')

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

        try:
            delete_monitor_task = form.cleaned_data.get('delete_monitor_task', False)
            act = obj.create_or_change_monitor_task(only_delete=delete_monitor_task)
            if act == 'create':
                self.message_user(request, _("为服务单元创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, _("更新了服务单元对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, _("删除了服务单元对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, _("创建或更新服务单元对应的站点监控任务错误") + str(exc), level=messages.ERROR)


@admin.register(ServicePrivateQuota)
class ServicePrivateQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__org_data_center', 'service')
    actions = ['quota_used_update']

    @admin.action(description=_("已用配额统计更新"))
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
    list_filter = ('service__org_data_center', 'service')
    actions = ['quota_used_update']

    @admin.action(description=_("已用配额统计更新"))
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


# @admin.register(ApplyVmService)
# class ApplyServiceAdmin(admin.ModelAdmin):
#     list_display_links = ('id',)
#     list_display = ('id', 'organization', 'name', 'name_en', 'service_type', 'status', 'user',
#                     'creation_time', 'approve_time')
#
#     list_filter = ('organization',)
#
#
