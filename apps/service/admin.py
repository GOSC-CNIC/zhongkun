from django.contrib import admin
from django.utils.translation import gettext_lazy, gettext as _
from django.utils.html import format_html
from django.contrib import messages
from django.contrib.admin.filters import SimpleListFilter
from django.db import transaction
from django.forms import ModelForm
from django_json_widget.widgets import JSONEditorWidget

from utils.model import NoDeleteSelectModelAdmin, BaseModelAdmin
from apps.service.odc_manager import OrgDataCenterManager
from apps.service.models import (
    DataCenter, Contacts, OrgDataCenter, OrgDataCenterAdminUser, KunYuanService
)
from apps.service.forms import KunYuanServiceForm
from apps.service.managers.kunyuan import KunYuanServiceManager


class ODCModelForm(ModelForm):
    class Meta:
        widgets = {
            'map_display': JSONEditorWidget(),
        }


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
    form = ODCModelForm
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
    readonly_fields = ('metric_task_id', 'log_task_id')
    fieldsets = (
        (gettext_lazy('数据中心基础信息'), {
            'fields': (
                'name', 'name_en', 'organization', 'sort_weight', 'longitude', 'latitude', 'remark', 'map_display'
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
    #
    # def save_related(self, request, form, formsets, change):
    #     new_users = form.cleaned_data['users']
    #     odc = form.instance
    #     old_users = odc.users.all()
    #     old_user_ids = [u.id for u in old_users]
    #
    #     add_users = []
    #     for u in new_users:
    #         if u.id in old_user_ids:
    #             old_user_ids.remove(u.id)    # 删除完未变的，剩余的都是将被删除的user
    #         else:
    #             add_users.append(u)
    #
    #     remove_user_ids = old_user_ids
    #     remove_users = []
    #     if remove_user_ids:
    #         for u in old_users:
    #             if u.id in remove_user_ids:
    #                 remove_users.append(u)
    #
    #     super(OrgDataCenterAdmin, self).save_related(request=request, form=form, formsets=formsets, change=change)
    #     if not remove_users and not add_users:
    #         return
    #
    #     try:
    #         OrgDataCenterManager.sync_odc_admin_to_pay_service(
    #             odc=odc, add_admins=add_users, remove_admins=remove_users)
    #     except Exception as exc:
    #         messages.add_message(
    #             request=request, level=messages.ERROR,
    #             message=_('数据中心管理员变更权限同步到钱包结算单元失败。' + str(exc)))
    #
    #     msg = _('数据中心管理员权限变更成功同步到钱包结算单元')
    #     if add_users:
    #         msg += ';' + _('新添加管理员') + f'{[u.username for u in add_users]}'
    #     if remove_users:
    #         msg += ';' + _('移除管理员') + f'{[u.username for u in remove_users]}'
    #
    #     messages.add_message(request=request, level=messages.SUCCESS, message=msg)

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


@admin.register(Contacts)
class ContactsAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'telephone', 'email', 'address', 'creation_time', 'remarks')


class ODCAdminODCFilter(SimpleListFilter):
    title = gettext_lazy("数据中心")
    parameter_name = 'odc_id'

    def lookups(self, request, model_admin):
        r = OrgDataCenter.objects.order_by('organization__sort_weight', 'sort_weight').values_list(
            'id', 'name', 'organization__name'
        )
        d = {i[0]: f'{i[2]}【{i[1]}】' for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(orgdatacenter_id=org_id)


@admin.register(OrgDataCenterAdminUser)
class OrgDataCenterAdminUserAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'show_org_name', 'orgdatacenter', 'userprofile', 'role', 'join_time')
    list_select_related = ('userprofile', 'orgdatacenter__organization')
    list_filter = (ODCAdminODCFilter,)
    raw_id_fields = ('userprofile', 'orgdatacenter')
    search_fields = ('userprofile__username', 'orgdatacenter__name', 'orgdatacenter__id')

    @admin.display(description=gettext_lazy('机构'))
    def show_org_name(self, obj):
        try:
            return obj.orgdatacenter.organization.name
        except Exception:
            return ''

    def save_model(self, request, obj: OrgDataCenterAdminUser, form, change):
        super().save_model(request=request, obj=obj, form=form, change=change)

        try:
            if obj.role == OrgDataCenterAdminUser.Role.ADMIN.value:
                add_tup, rm_tup_list = OrgDataCenterManager.sync_odc_admin_to_pay_service(
                    odc=obj.orgdatacenter, add_admins=[obj.userprofile], remove_admins=[])
                # msg = _('数据中心管理员权限变更成功同步添加到钱包结算单元')
                self._add_admin_to_pay_message(request=request, add_tuple=add_tup)
                self._rm_admin_to_pay_message(request=request, rm_tuple_list=rm_tup_list)
            else:
                add_tup, rm_tup_list = OrgDataCenterManager.sync_odc_admin_to_pay_service(
                    odc=obj.orgdatacenter, add_admins=[], remove_admins=[obj.userprofile])
                self._add_admin_to_pay_message(request=request, add_tuple=add_tup)
                self._rm_admin_to_pay_message(request=request, rm_tuple_list=rm_tup_list)
                # msg = _('数据中心管理员权限变更成功从钱包结算单元移除')
        except Exception as exc:
            messages.add_message(
                request=request, level=messages.ERROR,
                message=_('数据中心管理员变更权限同步到钱包结算单元失败。' + str(exc)))

    def delete_model(self, request, obj: OrgDataCenterAdminUser):
        with transaction.atomic():
            add_tup, rm_tup_list = OrgDataCenterManager.sync_odc_admin_to_pay_service(
                odc=obj.orgdatacenter, add_admins=[], remove_admins=[obj.userprofile])
            super().delete_model(request=request, obj=obj)
            self._add_admin_to_pay_message(request=request, add_tuple=add_tup)
            self._rm_admin_to_pay_message(request=request, rm_tuple_list=rm_tup_list)
            # messages.add_message(request=request, level=messages.SUCCESS,
            #                      message=_('数据中心管理员权限变更成功从钱包结算单元移除'))

    def delete_queryset(self, request, queryset):
        with transaction.atomic():
            for obj in queryset:
                add_tup, rm_tup_list = OrgDataCenterManager.sync_odc_admin_to_pay_service(
                    odc=obj.orgdatacenter, add_admins=[], remove_admins=[obj.userprofile])
                self._add_admin_to_pay_message(request=request, add_tuple=add_tup)
                self._rm_admin_to_pay_message(request=request, rm_tuple_list=rm_tup_list)

            super().delete_queryset(request=request, queryset=queryset)
            # messages.add_message(request=request, level=messages.SUCCESS,
            #                      message=_('数据中心管理员权限变更成功从钱包结算单元移除'))

    @staticmethod
    def _add_admin_to_pay_message(request, add_tuple: tuple):
        pay_services, users = add_tuple
        if pay_services and users:
            services = [f'"{s.name}({s.get_category_display()})"' for s in pay_services]
            admins = [u.username for u in users]
            msg = _('添加管理员[{users}]到钱包结算单元[{services}]').format(
                users=','.join(admins), services='、 '.join(services))
            messages.add_message(request=request, level=messages.SUCCESS, message=msg)

    @staticmethod
    def _rm_admin_to_pay_message(request, rm_tuple_list: list):
        for rm_tuple in rm_tuple_list:
            pay_services, user = rm_tuple
            if pay_services and user:
                services = [f'"{s.name}({s.get_category_display()})"' for s in pay_services]
                msg = _('从钱包结算单元[{services}]移除管理员[{users}]').format(
                    users=user.username, services='、 '.join(services))
                messages.add_message(request=request, level=messages.SUCCESS, message=msg)


class KunYuanServiceOrgFilter(SimpleListFilter):
    title = gettext_lazy("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        r = KunYuanService.objects.select_related('org_data_center__organization').order_by('sort_weight').values_list(
            'org_data_center__organization_id', 'org_data_center__organization__name'
        )
        d = {i[0]: i[1] for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(org_data_center__organization_id=org_id)


@admin.register(KunYuanService)
class KunYuanServiceAdmin(BaseModelAdmin):
    form = KunYuanServiceForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'org_data_center', 'organization_name', 'sort_weight',
                    'version', 'version_update_time',
                    'endpoint_url', 'username', 'password', 'raw_password',
                    'creation_time', 'status', 'longitude', 'latitude', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = [KunYuanServiceOrgFilter, 'status']
    list_select_related = ('org_data_center', 'org_data_center__organization')
    raw_id_fields = ('org_data_center',)
    list_editable = ('sort_weight',)

    readonly_fields = ('password',)

    actions = ['update_service_version']

    @admin.action(description=gettext_lazy("更新服务版本信息"))
    def update_service_version(self, request, queryset):
        count = 0
        for service in queryset:
            if service.status != KunYuanService.Status.ENABLE.value:
                continue

            ok = KunYuanServiceManager.update_service_version(service=service)
            if ok is True:
                count += 1

        if count > 0:
            self.message_user(request, _("更新版本数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, _("没有更新任何服务单元版本"), level=messages.SUCCESS)

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
