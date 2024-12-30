from django.contrib import admin, messages
from django.utils.translation import get_language, gettext, gettext_lazy as _
from django.utils.html import format_html
from django.db import transaction
from django.contrib.admin.filters import SimpleListFilter

from apps.app_storage.request import request_service
from apps.app_storage.adapter import inputs
from core import errors
from utils.model import NoDeleteSelectModelAdmin, BaseModelAdmin
from apps.app_storage.managers import ObjectsServiceManager
from apps.service.odc_manager import OrgDataCenterManager
from . import models
from . import forms


class StorageOrgOdcShowMixin:
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


class ServiceOrgFilter(SimpleListFilter):
    title = _("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        qs = models.ObjectsService.objects.select_related('org_data_center__organization').order_by('sort_weight')
        lang = get_language()
        if lang == 'en':
            r = qs.values_list('org_data_center__organization_id', 'org_data_center__organization__name_en')
        else:
            r = qs.values_list('org_data_center__organization_id', 'org_data_center__organization__name')

        d = {i[0]: i[1] for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(org_data_center__organization_id=org_id)


class BucketServiceFilter(SimpleListFilter):
    title = _("服务单元")
    parameter_name = 'service_id'

    def lookups(self, request, model_admin):
        qs = models.ObjectsService.objects.order_by('org_data_center__organization__sort_weight', 'sort_weight')
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


@admin.register(models.ObjectsService)
class ObjectsServiceAdmin(BaseModelAdmin):
    form = forms.ObjectsServiceForm

    list_display = ('id', 'name', 'name_en', 'org_data_center', 'organization_name', 'service_type',
                    'sort_weight', 'version', 'version_update_time', 'endpoint_url', 'add_time', 'status',
                    'username', 'raw_password', 'provide_ftp', 'pay_app_service_id', 'monitor_task_id')

    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = [ServiceOrgFilter,]
    list_select_related = ('org_data_center', 'org_data_center__organization')
    list_editable = ('sort_weight',)
    raw_id_fields = ('org_data_center',)

    filter_horizontal = ('users',)
    readonly_fields = ('password', 'monitor_task_id')
    fieldsets = (
        (_('说明、备注'), {'fields': ('remarks', 'sort_weight')}),
        (_('服务配置信息'), {
            'fields': ('org_data_center', 'name', 'name_en', 'service_type', 'version', 'version_update_time',
                       'status', 'endpoint_url', 'api_version', 'username', 'password', 'change_password')
        }),
        (_('FTP配置信息'), {
            'fields': ('provide_ftp', 'ftp_domains')
        }),
        (_('支付结算信息'), {'fields': ('pay_app_service_id',)}),
        (_('其他配置信息'), {'fields': ('extra', 'logo_url', 'longitude', 'latitude')}),
        (_('服务管理员'), {'fields': ('users',)}),
        (_('联系人信息'), {
            'fields': ('contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address')
        }),
        (_('其他'), {'fields': ('monitor_task_id', 'create_monitor_task',)}),
    )
    actions = ['update_service_version']

    @admin.display(description=_("原始密码"))
    def raw_password(self, obj):
        passwd = obj.raw_password
        if not passwd:
            return passwd

        return format_html(f'<div title="{passwd}">******</div>')

    @admin.display(description=_("机构"))
    def organization_name(self, obj):
        if not obj.org_data_center or not obj.org_data_center.organization:
            return ''

        return obj.org_data_center.organization.name

    @admin.action(description=_("更新服务版本信息"))
    def update_service_version(self, request, queryset):
        count = 0
        for service in queryset:
            if (
                    service.status != models.ObjectsService.Status.ENABLE.value
                    or service.service_type != models.ObjectsService.ServiceType.IHARBOR.value
            ):
                continue

            ok = ObjectsServiceManager.update_service_version(service=service)
            if ok is True:
                count += 1

        if count > 0:
            self.message_user(request, gettext("更新版本数量:") + str(count), level=messages.SUCCESS)
        else:
            self.message_user(request, gettext("没有更新任何服务单元版本"), level=messages.SUCCESS)

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj: models.ObjectsService, form: forms.ObjectsServiceForm, change):
        in_custom_admin_changelist = getattr(request, 'in_custom_admin_changelist', None)
        if in_custom_admin_changelist:
            return super().save_model(request=request, obj=obj, form=form, change=change)

        if change:
            super().save_model(request=request, obj=obj, form=form, change=change)
            try:
                obj.sync_to_pay_app_service()
            except Exception as exc:
                self.message_user(request, gettext("更新服务单元对应的结算服务单元错误") + str(exc), level=messages.ERROR)
        else:   # add
            with transaction.atomic():
                super().save_model(request=request, obj=obj, form=form, change=change)
                obj.check_or_register_pay_app_service()

        try:
            create_monitor_task = form.cleaned_data.get('create_monitor_task', False)
            act = obj.create_or_change_monitor_task(only_delete=not create_monitor_task)
            if act == 'create':
                self.message_user(request, gettext("为服务单元创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, gettext("更新了服务单元对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, gettext("删除了服务单元对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, gettext("创建或更新服务单元对应的站点监控任务错误") + str(exc), level=messages.ERROR)

    def save_related(self, request, form, formsets, change):
        in_custom_admin_changelist = getattr(request, 'in_custom_admin_changelist', None)
        if in_custom_admin_changelist:
            return super(ObjectsServiceAdmin, self).save_related(
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

        super(ObjectsServiceAdmin, self).save_related(request=request, form=form, formsets=formsets, change=change)
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
        respone = super(ObjectsServiceAdmin, self).changelist_view(request=request, extra_context=extra_context)
        return respone


@admin.register(models.Bucket)
class BucketAdmin(NoDeleteSelectModelAdmin, StorageOrgOdcShowMixin):
    list_display = ('id', 'name', 'bucket_id',
                    StorageOrgOdcShowMixin.SHOW_ORG_NAME, StorageOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'creation_time', 'user',
                    'task_status', 'situation', 'situation_time', 'storage_size', 'object_count',
                    'stats_time', 'tag')
    list_select_related = ('service__org_data_center__organization', 'user')
    raw_id_fields = ('user', 'service')
    list_filter = [BucketServiceFilter, 'situation', 'task_status', 'tag']
    search_fields = ['name', 'user__username', 'id']

    def delete_model(self, request, obj):
        bucket = obj

        try:
            params = inputs.BucketDeleteInput(bucket_name=bucket.name, username=bucket.user.username)
            r = request_service(service=bucket.service, method='bucket_delete', params=params)
            bucket.do_archive(archiver=request.user.username)
        except errors.Error as exc:
            if 'Adapter.BucketNotOwned' != exc.code:
                self.message_user(request=request, message=gettext('删除失败，') + str(exc), level=messages.ERROR)
                raise exc
        except Exception as exc:
            self.message_user(request=request, message=gettext('删除失败，') + str(exc), level=messages.ERROR)
            raise exc


@admin.register(models.BucketArchive)
class BucketArchiveAdmin(BaseModelAdmin, StorageOrgOdcShowMixin):
    list_display = ('id', 'name',
                    StorageOrgOdcShowMixin.SHOW_ORG_NAME, StorageOrgOdcShowMixin.SHOW_ODC_NAME,
                    'service', 'creation_time', 'user', 'delete_time', 'archiver',
                    'task_status', 'situation', 'situation_time', 'storage_size', 'object_count',
                    'stats_time', 'tag')
    list_select_related = ('service__org_data_center__organization', 'user')
    raw_id_fields = ('user', 'service')
    search_fields = ['name', 'user__username', 'original_id']
    list_filter = [BucketServiceFilter, 'situation', 'task_status', 'tag']

    def has_delete_permission(self, request, obj=None):
        return False
