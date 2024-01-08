from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _
from django.utils.html import format_html
from django.contrib import messages
from django.db import transaction
from django.contrib.admin.filters import SimpleListFilter

from servers.models import Server, Disk
from utils.model import NoDeleteSelectModelAdmin
from .odc_manager import OrgDataCenterManager
from .models import (
    ServiceConfig, DataCenter, ServicePrivateQuota,
    ServiceShareQuota, ApplyVmService, ApplyOrganization, Contacts,
    OrgDataCenter
)
from . import forms


class ServiceOrgFilter(SimpleListFilter):
    title = gettext_lazy("机构")
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
    form = forms.VmsProviderForm
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
        (gettext_lazy('说明、备注'), {'fields': ('remarks', 'sort_weight', 'only_admin_visible')}),
        (gettext_lazy('服务配置信息'), {
            'fields': ('org_data_center', 'name', 'name_en', 'service_type', 'cloud_type', 'status', 'endpoint_url',
                       'api_version', 'region_id', 'disk_available', 'username', 'password', 'change_password')
        }),
        (gettext_lazy('VPN配置信息'), {
            'fields': ('need_vpn', 'vpn_endpoint_url', 'vpn_api_version', 'vpn_username',
                       'vpn_password', 'change_vpn_password')
        }),
        (gettext_lazy('支付结算信息'), {'fields': ('pay_app_service_id',)}),
        (gettext_lazy('其他配置信息'), {'fields': ('extra', 'logo_url', 'longitude', 'latitude')}),
        (gettext_lazy('服务管理员'), {'fields': ('users', )}),
        (gettext_lazy('联系人信息'), {
            'fields': ('contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address')
        }),
        (gettext_lazy('监控任务'), {'fields': ('monitor_task_id', 'delete_monitor_task')}),
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

    @admin.display(description=gettext_lazy("原始密码"))
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


@admin.register(DataCenter)
class DataCenterAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'abbreviation', 'status', 'sort_weight',
                    'creation_time', 'longitude', 'latitude', 'desc')
    list_editable = ('sort_weight', )
    search_fields = ('name', 'name_en', 'abbreviation')
    filter_horizontal = ('contacts',)


class ODCOrgFilter(SimpleListFilter):
    title = gettext_lazy("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        r = OrgDataCenter.objects.order_by('organization__sort_weight').values_list(
            'organization_id', 'organization__name'
        )
        d = {i[0]: i[1] for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(organization_id=org_id)


@admin.register(OrgDataCenter)
class OrgDataCenterAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'organization', 'sort_weight', 'longitude', 'latitude', 'creation_time',
                    'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                    'metric_monitor_url', 'metric_task_id',
                    'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url',
                    'log_monitor_url', 'log_task_id'
                    )
    search_fields = ['name', 'name_en', 'thanos_endpoint_url', 'loki_endpoint_url', 'remark']
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)
    list_editable = ('sort_weight',)
    list_filter = (ODCOrgFilter,)
    filter_horizontal = ('users',)
    readonly_fields = ('metric_task_id', 'log_task_id')
    fieldsets = (
        (gettext_lazy('数据中心基础信息'), {
            'fields': (
                'name', 'name_en', 'organization', 'sort_weight', 'longitude', 'latitude', 'remark',
                'users'
            )
        }),
        (gettext_lazy('指标监控系统'), {
            'fields': (
                'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
                'metric_monitor_url', 'metric_task_id'
            )
        }),
        (gettext_lazy('日志聚合系统'), {
            'fields': (
                'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark',
                'log_monitor_url', 'log_task_id'
            )
        }),
    )

    def save_related(self, request, form, formsets, change):
        new_users = form.cleaned_data['users']
        odc = form.instance
        old_users = odc.users.all()
        old_user_ids = [u.id for u in old_users]

        add_users = []
        for u in new_users:
            if u.id in old_user_ids:
                old_user_ids.remove(u.id)    # 删除完未变的，剩余的都是将被删除的user
            else:
                add_users.append(u)

        remove_user_ids = old_user_ids
        remove_users = []
        if remove_user_ids:
            for u in old_users:
                if u.id in remove_user_ids:
                    remove_users.append(u)

        super(OrgDataCenterAdmin, self).save_related(request=request, form=form, formsets=formsets, change=change)
        if not remove_users and not add_users:
            return

        try:
            OrgDataCenterManager.sync_odc_admin_to_pay_service(
                odc=odc, add_admins=add_users, remove_admins=remove_users)
        except Exception as exc:
            messages.add_message(
                request=request, level=messages.ERROR,
                message=_('数据中心管理员变更权限同步到钱包结算单元失败。' + str(exc)))

        msg = _('数据中心管理员权限变更成功同步到钱包结算单元')
        if add_users:
            msg += ';' + _('新添加管理员') + f'{[u.username for u in add_users]}'
        if remove_users:
            msg += ';' + _('移除管理员') + f'{[u.username for u in remove_users]}'

        messages.add_message(request=request, level=messages.SUCCESS, message=msg)

    def save_model(self, request, obj: OrgDataCenter, form, change):
        super().save_model(request=request, obj=obj, form=form, change=change)

        try:
            act = OrgDataCenterManager.create_or_change_metric_monitor_task(odc=obj)
            if act == 'create':
                self.message_user(request, _("为数据中心的指标监控系统监控网址创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, _("更新了数据中心的指标监控系统对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, _("删除了数据中心的指标监控系统对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, _("创建或更新数据中心的指标监控系统对应的站点监控任务错误") + str(exc),
                              level=messages.ERROR)

        try:
            act = OrgDataCenterManager.create_or_change_log_monitor_task(odc=obj)
            if act == 'create':
                self.message_user(request, _("为数据中心的日志聚合系统监控网址创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, _("更新了数据中心的日志聚合系统对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, _("删除了数据中心的日志聚合系统对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, _("创建或更新数据中心的日志聚合系统对应的站点监控任务错误") + str(exc),
                              level=messages.ERROR)


@admin.register(ServicePrivateQuota)
class ServicePrivateQuotaAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service',)
    list_filter = ('service__org_data_center', 'service')
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
    list_filter = ('service__org_data_center', 'service')
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
