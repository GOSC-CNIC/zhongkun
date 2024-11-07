from django.contrib import admin, messages
from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import get_language, gettext, gettext_lazy as _
from django.utils.html import format_html
from django.db import transaction
from django import forms
from django.contrib.admin import helpers
from django.core.exceptions import ValidationError

from core import request as core_request
from utils.model import NoDeleteSelectModelAdmin, PayType, BaseModelAdmin
from apps.servers.forms import VmsProviderForm
from apps.servers.models import (
    Server, Flavor, ServerArchive, Disk, ResourceActionLog, DiskChangeLog,
    ServiceConfig, ServicePrivateQuota, ServerSnapshot, EVCloudPermsLog
)
from apps.servers.managers import ServiceManager
from apps.servers.tasks import update_services_server_count
from apps.service.odc_manager import OrgDataCenterManager
from apps.service.models import OrgDataCenter


class ServerOrgOdcShowMixin:
    SHOW_ORG_NAME = 'show_org_name'
    SHOW_ODC_NAME = 'show_odc_name'

    @admin.display(description=_('机构'))
    def show_org_name(self, obj):
        try:
            lang = get_language()
            if lang == 'en':
                return obj.service.org_data_center.organization.name_en
            else:
                return obj.service.org_data_center.organization.name
        except Exception:
            return ''

    @admin.display(description=_('数据中心'))
    def show_odc_name(self, obj):
        if not obj.service or not obj.service.org_data_center:
            return ''

        lang = get_language()
        if lang == 'en':
            return obj.service.org_data_center.name_en
        else:
            return obj.service.org_data_center.name


class ServerAdminForm(forms.ModelForm):
    change_password = forms.CharField(
        label=_('更改默认登录密码输入'), required=False, min_length=3, max_length=32,
        help_text=_('如果要更改默认登录密码，请在此输入新密码, 不修改请保持为空'))

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        if change_password:
            self.instance.raw_default_password = change_password

        return super().save(commit=commit)

    def clean(self):
        cleaned_data = self.cleaned_data
        service = cleaned_data['service']
        instance_id = cleaned_data['instance_id']
        if not service:
            raise ValidationError(message={'service': gettext('必须选择服务单元')})

        if not instance_id:
            raise ValidationError(message={'instance_id': gettext('必须填写服务单元中云主机ID')})

        qs = Server.objects.filter(service_id=service.id, instance_id=instance_id)
        ins = self.instance
        if qs.exclude(id=ins.id).exists():
            raise ValidationError(message={'instance_id': gettext('已存在此服务单元云主机ID')})


class ServerODCFilter(SimpleListFilter):
    title = _("数据中心")
    parameter_name = 'odc_id'

    def lookups(self, request, model_admin):
        qs = OrgDataCenter.objects.order_by('organization__sort_weight', 'sort_weight')
        lang = get_language()
        if lang == 'en':
            r = qs.values_list('id', 'name_en', 'organization__name_en')
        else:
            r = qs.values_list('id', 'name', 'organization__name')

        d = {i[0]: f'{i[2]}【{i[1]}】' for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        odc_id = request.GET.get(self.parameter_name)
        if odc_id:
            return queryset.filter(service__org_data_center_id=odc_id)


class ServerServiceFilter(SimpleListFilter):
    title = _("服务单元")
    parameter_name = 'service_id'

    def lookups(self, request, model_admin):
        qs = ServiceConfig.objects.order_by('org_data_center__organization__sort_weight', 'sort_weight')

        lang = get_language()
        if lang == 'en':
            r = qs.values_list('id', 'name_en', 'org_data_center__name_en', 'org_data_center__organization__name_en')
        else:
            r = qs.values_list('id', 'name', 'org_data_center__name', 'org_data_center__organization__name')

        d = {i[0]: f'{i[3]} / {i[2]} /【{i[1]}】' for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        service_id = request.GET.get(self.parameter_name)
        if service_id:
            return queryset.filter(service_id=service_id)


@admin.register(Server)
class ServerAdmin(NoDeleteSelectModelAdmin, ServerOrgOdcShowMixin):
    form = ServerAdminForm
    list_display_links = ('id',)
    list_display = ('id', ServerOrgOdcShowMixin.SHOW_ORG_NAME, ServerOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'azone_id', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                    'creation_time', 'start_time', 'user', 'task_status', 'center_quota',
                    'pay_type', 'classification', 'vo', 'created_user', 'lock', 'situation', 'situation_time',
                    'default_user', 'show_default_password', 'expiration_time', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = [ServerODCFilter, ServerServiceFilter, 'classification', 'public_ip']
    raw_id_fields = ('user', )
    list_select_related = ('service__org_data_center__organization', 'user', 'vo')
    readonly_fields = ['default_password']

    fieldsets = [
        (_('基础信息'), {'fields': ('service', 'azone_id', 'instance_id', 'remarks', 'center_quota')}),
        (_('配置信息'), {'fields': (
            'vcpus', 'ram', 'disk_size', 'ipv4', 'public_ip', 'image_id', 'image', 'img_sys_type',
            'img_sys_arch', 'img_release', 'img_release_version', 'image_desc')}),
        (_('默认登录密码'), {'fields': ('default_user', 'default_password', 'change_password')}),
        (_('创建和归属信息'), {'fields': ('creation_time', 'task_status', 'classification', 'user', 'vo')}),
        (_('计量和管控信息'), {'fields': (
            'pay_type', 'start_time', 'expiration_time', 'lock', 'situation', 'situation_time')}),
    ]
    actions = ['update_server_info',]

    @admin.action(description=_("从服务单元更新云主机的基本信息"))
    def update_server_info(self, request, queryset):
        """
        从服务单元更新云主机的基本信息
        """
        count = 0
        failed_count = 0
        msg = ''
        for server in queryset:
            try:
                core_request.update_server_detail(server=server)
                count += 1
            except Exception as exc:
                msg = str(exc)
                failed_count += 1

        if count > 0:
            self.message_user(
                request,
                gettext("成功更新云主机数量%(count)s，失败%(failed)s") % {'count': count, 'failed': failed_count},
                level=messages.SUCCESS)
        elif failed_count:
            self.message_user(request, gettext("更新云主机全部失败") + msg, level=messages.WARNING)
        else:
            self.message_user(request, gettext("没有更新任何云主机"), level=messages.SUCCESS)

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
class ServerArchiveAdmin(NoDeleteSelectModelAdmin, ServerOrgOdcShowMixin):
    list_display_links = ('id',)
    list_display = ('id', ServerOrgOdcShowMixin.SHOW_ORG_NAME, ServerOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'name', 'instance_id',
                    'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                    'creation_time', 'user', 'task_status', 'pay_type', 'classification', 'vo',
                    'created_user', 'center_quota',
                    'start_time', 'deleted_time', 'archive_user', 'archive_type', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['archive_type', ServerServiceFilter, 'classification']
    raw_id_fields = ('user',)
    list_select_related = ('service__org_data_center__organization', 'user', 'archive_user', 'vo')
    show_full_result_count = False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False


@admin.register(Flavor)
class FlavorAdmin(BaseModelAdmin, ServerOrgOdcShowMixin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'service',
                    ServerOrgOdcShowMixin.SHOW_ORG_NAME, ServerOrgOdcShowMixin.SHOW_ODC_NAME, 'creation_time')
    ordering = ('vcpus', 'ram')
    list_filter = [ServerServiceFilter]
    list_select_related = ('service__org_data_center__organization',)


@admin.register(Disk)
class DiskAdmin(NoDeleteSelectModelAdmin, ServerOrgOdcShowMixin):
    list_display_links = ('id',)
    list_display = ('id', ServerOrgOdcShowMixin.SHOW_ORG_NAME, ServerOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'azone_id', 'azone_name', 'size', 'instance_id', 'quota_type',
                    'creation_time', 'task_status', 'expiration_time', 'start_time', 'pay_type',
                    'classification', 'user', 'vo', 'created_user', 'lock',
                    'show_deleted', 'deleted_time', 'deleted_user',
                    'server', 'mountpoint', 'attached_time', 'detached_time', 'remarks')
    search_fields = ['id', 'instance_id', 'server__id', 'remarks', 'user__username']
    list_filter = [ServerODCFilter, ServerServiceFilter, 'classification', 'deleted']
    raw_id_fields = ('user', 'vo', 'server')
    list_select_related = ('service__org_data_center__organization', 'user', 'vo', 'server')
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
    list_filter = ['log_type', ServerServiceFilter, 'classification']
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
                    'only_admin_visible', 'region_id', 'service_type', 'version', 'version_update_time',
                    'endpoint_url', 'username', 'password', 'raw_password',
                    'add_time', 'status', 'need_vpn', 'disk_available',
                    'vpn_endpoint_url', 'vpn_password', 'server_managed', 'server_total', 'server_update_time',
                    'pay_app_service_id', 'longitude', 'latitude', 'remarks', 'monitor_task_id')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['service_type', 'disk_available', ServiceOrgFilter, 'status']
    list_select_related = ('org_data_center', 'org_data_center__organization')
    raw_id_fields = ('org_data_center',)
    list_editable = ('sort_weight',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', 'vpn_password', 'monitor_task_id')
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks', 'sort_weight', 'only_admin_visible')}),
        (_('服务配置信息'), {
            'fields': ('org_data_center', 'name', 'name_en', 'service_type', 'cloud_type',
                       'version', 'version_update_time', 'status', 'endpoint_url',
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
        (_('监控任务'), {'fields': ('monitor_task_id', 'create_monitor_task')}),
    )

    actions = ['encrypt_password', 'encrypt_vpn_password', 'update_service_version', 'update_server_count_stats']

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
            self.message_user(request, gettext("加密更新数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, gettext("没有加密更新任何数据记录"), level=messages.SUCCESS)

    @admin.action(description=_("更新服务版本信息"))
    def update_service_version(self, request, queryset):
        count = 0
        for service in queryset:
            service: ServiceConfig
            if (
                    service.status != ServiceConfig.Status.ENABLE.value
                    or service.service_type != ServiceConfig.ServiceType.EVCLOUD.value
            ):
                continue

            ok = ServiceManager.update_service_version(service=service)
            if ok is True:
                count += 1

        if count > 0:
            self.message_user(request, gettext("更新版本数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, gettext("没有更新任何服务单元版本"), level=messages.SUCCESS)

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
        in_custom_admin_changelist = getattr(request, 'in_custom_admin_changelist', None)
        if in_custom_admin_changelist:
            return super().save_model(request=request, obj=obj, form=form, change=change)

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
            create_monitor_task = form.cleaned_data.get('create_monitor_task', True)
            act = obj.create_or_change_monitor_task(only_delete=not create_monitor_task)
            if act == 'create':
                self.message_user(request, _("为服务单元创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, _("更新了服务单元对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, _("删除了服务单元对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, _("创建或更新服务单元对应的站点监控任务错误") + str(exc), level=messages.ERROR)

    def save_related(self, request, form, formsets, change):
        in_custom_admin_changelist = getattr(request, 'in_custom_admin_changelist', None)
        if in_custom_admin_changelist:
            return super(ServiceConfigAdmin, self).save_related(
                request=request, form=form, formsets=formsets, change=change)

        new_users = form.cleaned_data['users']
        service = form.instance
        old_users = service.users.all()
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

        super(ServiceConfigAdmin, self).save_related(request=request, form=form, formsets=formsets, change=change)
        if not remove_users and not add_users:
            return

        pay_app_service_id = service.pay_app_service_id
        if not pay_app_service_id:
            return

        not_need_remove_admins = []  # 数据中心管理员不需要移除
        try:
            # 如果是数据中心管理员的，不需要移除钱包权限
            if remove_users and service.org_data_center_id:
                odc_id = service.org_data_center_id
                admin_map = OrgDataCenterManager.get_odc_admins_map(
                    odc_ids=[odc_id], admin=True, ops=False)
                if odc_id in admin_map:
                    odc_admin_dict = admin_map.get(odc_id)
                    new_remove_users = []
                    for u in remove_users:
                        if u.id in odc_admin_dict:
                            not_need_remove_admins.append(u)
                        else:
                            new_remove_users.append(u)

                    remove_users = new_remove_users

            if not remove_users and not add_users:
                if not_need_remove_admins:
                    msg = _('因为是数据中心管理员而不需要从钱包移除的管理员') + f'{[u.username for u in not_need_remove_admins]}'
                    messages.add_message(request=request, level=messages.SUCCESS, message=msg)
                return

            pay_service = OrgDataCenterManager.sync_admin_to_one_pay_service(
                pay_service_or_id=pay_app_service_id, add_admins=add_users, remove_admins=remove_users)
        except Exception as exc:
            messages.add_message(
                request=request, level=messages.ERROR,
                message=_('服务单元管理员变更权限同步到钱包结算单元失败。' + str(exc)))
            return

        if pay_service is None:
            messages.add_message(
                request=request, level=messages.WARNING,
                message=gettext('服务单元未配置钱包结算单元信息，管理员权限变更未同步到钱包。'))
            return

        msg = _('服务单元管理员权限变更成功同步到钱包结算单元')
        if add_users:
            msg += ';' + _('新添加管理员') + f'{[u.username for u in add_users]}'
        if remove_users:
            msg += ';' + _('移除管理员') + f'{[u.username for u in remove_users]}'
        if not_need_remove_admins:
            msg += ';' + _('因为是数据中心管理员而不需要移除的管理员') + f'{[u.username for u in not_need_remove_admins]}'

        messages.add_message(request=request, level=messages.SUCCESS, message=msg)

    def changelist_view(self, request, extra_context=None):
        request.in_custom_admin_changelist = True

        if request.method == "POST":
            action = self.get_actions(request)[request.POST['action']][0]
            act_not_need_selected = getattr(action, 'act_not_need_selected', False)
            if act_not_need_selected:
                post = request.POST.copy()
                post.setlist(helpers.ACTION_CHECKBOX_NAME, [0])
                request.POST = post

        respone = super(ServiceConfigAdmin, self).changelist_view(request=request, extra_context=extra_context)
        return respone

    @admin.action(description=_('更新服务单元云主机数信息'))
    def update_server_count_stats(self, request, queryset):
        update_services_server_count(update_ago_minutes=0)

    update_server_count_stats.act_not_need_selected = True


@admin.register(ServicePrivateQuota)
class ServicePrivateQuotaAdmin(BaseModelAdmin, ServerOrgOdcShowMixin):
    list_display_links = ('id',)
    list_display = ('id', ServerOrgOdcShowMixin.SHOW_ORG_NAME, ServerOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
                    'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
                    'enable', 'creation_time')
    list_select_related = ('service__org_data_center__organization',)
    list_filter = (ServerODCFilter, ServerServiceFilter)
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


@admin.register(ServerSnapshot)
class ServerSnapshotAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'size', 'creation_time', 'system_name', 'system_release',
                    'pay_type', 'expiration_time', 'remarks',
                    'classification', 'user', 'vo', 'server', 'show_deleted', 'deleted_time', 'deleted_user')
    list_select_related = ('user', 'vo', 'service', 'server')
    list_filter = (ServerServiceFilter, 'deleted')
    raw_id_fields = ('user', 'vo', 'server')
    search_fields = ['remarks', 'system_name']

    @admin.display(description=_('删除状态'))
    def show_deleted(self, obj):
        if obj.deleted:
            return gettext('已删除')

        return gettext('正常')


@admin.register(EVCloudPermsLog)
class EVCloudPermsLogAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'server', 'status', 'num', 'remarks', 'creation_time', 'update_time')
    list_select_related = ('server',)
    list_filter = ('status',)
    raw_id_fields = ('server',)
    search_fields = ['remarks', 'server__ipv4']


# @admin.register(ServiceShareQuota)
# class ServiceShareQuotaAdmin(admin.ModelAdmin):
#     list_display_links = ('id',)
#     list_display = ('id', 'service', 'vcpu_total', 'vcpu_used', 'ram_total', 'ram_used', 'disk_size_total',
#                     'disk_size_used', 'private_ip_total', 'private_ip_used', 'public_ip_total', 'public_ip_used',
#                     'enable', 'creation_time')
#     list_select_related = ('service',)
#     list_filter = ('service__org_data_center', 'service')
#     actions = ['quota_used_update']
#
#     @admin.action(description=_("已用配额统计更新"))
#     def quota_used_update(self, request, queryset):
#         failed_count = 0
#         for q in queryset:
#             r = Server.count_share_quota_used(q.service_id)
#
#             with transaction.atomic():
#                 quota = ServiceShareQuota.objects.select_for_update().get(id=q.id)
#                 update_fields = []
#                 vcpu_used_count = r.get('vcpu_used_count', None)
#                 if isinstance(vcpu_used_count, int) and quota.vcpu_used != vcpu_used_count:
#                     quota.vcpu_used = vcpu_used_count
#                     update_fields.append('vcpu_used')
#
#                 ram_used_count = r.get('ram_used_count', None)
#                 if isinstance(ram_used_count, int) and quota.ram_used_gib != ram_used_count:
#                     quota.ram_used_gib = ram_used_count
#                     update_fields.append('ram_used')
#
#                 public_ip_count = r.get('public_ip_count', None)
#                 if isinstance(public_ip_count, int) and quota.public_ip_used != public_ip_count:
#                     quota.public_ip_used = public_ip_count
#                     update_fields.append('public_ip_used')
#
#                 private_ip_used = r.get('private_ip_count', None)
#                 if isinstance(private_ip_used, int) and quota.private_ip_used != private_ip_used:
#                     quota.private_ip_used = private_ip_used
#                     update_fields.append('private_ip_used')
#
#                 if update_fields:
#                     try:
#                         quota.save(update_fields=update_fields)
#                     except Exception as e:
#                         failed_count += 1
#
#         if failed_count != 0:
#             self.message_user(request, _("统计更新已用配额失败") + f'({failed_count})', level=messages.ERROR)
#         else:
#             self.message_user(request, _("统计更新已用配额成功"), level=messages.SUCCESS)
