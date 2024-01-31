from django.contrib import admin, messages
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.html import format_html
from django.db import transaction
from django.contrib.admin.filters import SimpleListFilter

from storage.request import request_service
from storage.adapter import inputs
from core import errors
from utils.model import NoDeleteSelectModelAdmin, BaseModelAdmin
from . import models
from . import forms


class ServiceOrgFilter(SimpleListFilter):
    title = _("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        r = models.ObjectsService.objects.select_related(
            'org_data_center__organization').order_by('sort_weight').values_list(
            'org_data_center__organization_id', 'org_data_center__organization__name'
        )
        d = {i[0]: i[1] for i in r}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(org_data_center__organization_id=org_id)


@admin.register(models.ObjectsService)
class ObjectsServiceAdmin(BaseModelAdmin):
    form = forms.ObjectsServiceForm

    list_display = ('id', 'name', 'name_en', 'org_data_center', 'organization_name', 'service_type',
                    'sort_weight', 'endpoint_url', 'add_time', 'status',
                    'username', 'raw_password', 'provide_ftp', 'pay_app_service_id', 'monitor_task_id', 'loki_tag')

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
            'fields': ('org_data_center', 'name', 'name_en', 'service_type', 'status', 'endpoint_url',
                       'api_version', 'username', 'password', 'change_password')
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
        (_('其他'), {'fields': ('monitor_task_id', 'delete_monitor_task', 'loki_tag',)}),
    )

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

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj: models.ObjectsService, form: forms.ObjectsServiceForm, change):
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
            delete_monitor_task = form.cleaned_data.get('delete_monitor_task', False)
            act = obj.create_or_change_monitor_task(only_delete=delete_monitor_task)
            if act == 'create':
                self.message_user(request, gettext("为服务单元创建了对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'change':
                self.message_user(request, gettext("更新了服务单元对应的站点监控任务"), level=messages.SUCCESS)
            elif act == 'delete':
                self.message_user(request, gettext("删除了服务单元对应的站点监控任务"), level=messages.SUCCESS)
        except Exception as exc:
            self.message_user(request, gettext("创建或更新服务单元对应的站点监控任务错误") + str(exc), level=messages.ERROR)


@admin.register(models.Bucket)
class BucketAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'name', 'bucket_id', 'service', 'creation_time', 'user',
                    'task_status', 'situation', 'situation_time', 'storage_size', 'object_count',
                    'stats_time', 'tag')
    list_select_related = ('service', 'user')
    raw_id_fields = ('user',)
    list_filter = ['service', 'situation', 'task_status', 'tag']
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
class BucketArchiveAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'service', 'creation_time', 'user', 'delete_time', 'archiver',
                    'task_status', 'situation', 'situation_time', 'storage_size', 'object_count',
                    'stats_time', 'tag')
    list_select_related = ('service', 'user')
    raw_id_fields = ('user',)
    search_fields = ['name', 'user__username', 'original_id']
    list_filter = ['service', 'situation', 'task_status', 'tag']

    def has_delete_permission(self, request, obj=None):
        return False
