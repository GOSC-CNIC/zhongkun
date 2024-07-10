from datetime import datetime

from django import forms
from django.core.exceptions import ValidationError
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.utils.translation import gettext_lazy, gettext
from django.utils import timezone as dj_timezone
from django.utils.html import format_html


from utils.model import BaseModelAdmin, NoDeleteSelectModelAdmin
from apps.app_screenvis.configs_manager import screen_configs
from apps.app_screenvis.managers import ScreenWebMonitorManager
from .models import (
    ScreenConfig, MetricMonitorUnit, LogMonitorUnit,
    ServerService, ObjectService, ServerServiceTimedStats, ObjectServiceTimedStats, VPNTimedStats,
    ObjectServiceLog, ServerServiceLog, HostNetflow, WebsiteMonitorTask
)


@admin.register(ScreenConfig)
class ScreenConfigAdmin(BaseModelAdmin):
    list_display_links = ('id', 'name')
    list_display = ('id', 'name', 'value', 'creation_time', 'remark')
    search_fields = ('name', 'value')
    actions = ('update_configs',)
    show_full_result_count = False

    @admin.action(description=gettext_lazy('清理更新配置项'))
    def update_configs(self, request, queryset):
        screen_configs.clear_cache()
        screen_configs.get_configs()

    update_configs.act_not_need_selected = True

    def changelist_view(self, request, extra_context=None):
        if request.method == "POST":
            action = self.get_actions(request)[request.POST['action']][0]
            act_not_need_selected = getattr(action, 'act_not_need_selected', False)
            if act_not_need_selected:
                post = request.POST.copy()
                post.setlist(helpers.ACTION_CHECKBOX_NAME, [0])
                request.POST = post

        return super().changelist_view(request, extra_context)

    def get_changelist_instance(self, request):
        cl = super().get_changelist_instance(request)
        cl.show_admin_actions = True
        return cl


@admin.register(MetricMonitorUnit)
class MetricMonitorUnitAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'name_en', 'unit_type', 'sort_weight',
                    'job_tag', 'metric_endpoint_url', 'prometheus', 'creation_time', 'update_time')
    list_display_links = ('id', 'name')
    list_editable = ('sort_weight',)
    search_fields = ('name', 'name_en', 'job_tag',)

    @admin.display(description=gettext_lazy("指标监控系统url"))
    def metric_endpoint_url(self, obj):
        return screen_configs.get(screen_configs.ConfigName.METRIC_QUERY_ENDPOINT_URL.value)


# @admin.register(LogMonitorUnit)
class LogMonitorUnitAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'name_en', 'log_type', 'sort_weight',
                    'job_tag', 'creation_time', 'update_time')
    list_display_links = ('id', 'name')
    list_editable = ('sort_weight',)
    list_filter = ('log_type',)
    search_fields = ('name', 'name_en', 'job_tag',)


class ServiceForm(forms.ModelForm):
    change_password = forms.CharField(
        label=gettext_lazy('更改用户密码输入'), required=False, min_length=6, max_length=32,
        help_text=gettext_lazy('如果要更改服务认证用户密码，请在此输入新密码, 不修改请保持为空'))

    class Meta:
        widgets = {
            'remarks': forms.Textarea(attrs={'cols': 80, 'rows': 6}),
            "password": forms.PasswordInput(
                attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),
        }

    def save(self, commit=True):
        change_password = self.cleaned_data.get('change_password')      # 如果输入新密码则更改
        if change_password:
            self.instance.set_password(change_password)

        return super().save(commit=commit)


@admin.register(ServerService)
class ServerServiceAdmin(BaseModelAdmin):
    form = ServiceForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'status', 'sort_weight', 'endpoint_url',
                    'username', 'password', 'raw_password', 'creation_time', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_editable = ('sort_weight', 'status')

    readonly_fields = ('password',)

    @admin.display(description=gettext_lazy("原始密码"))
    def raw_password(self, obj):
        passwd = obj.raw_password()
        if not passwd:
            return passwd

        return format_html(f'<div title="{passwd}">******</div>')


@admin.register(ObjectService)
class ObjectServiceAdmin(BaseModelAdmin):
    form = ServiceForm
    list_display_links = ('id',)
    list_display = ('id', 'name', 'name_en', 'status', 'sort_weight', 'endpoint_url',
                    'username', 'password', 'raw_password', 'creation_time', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_editable = ('sort_weight', 'status')

    readonly_fields = ('password',)

    @admin.display(description=gettext_lazy("原始密码"))
    def raw_password(self, obj):
        passwd = obj.raw_password()
        if not passwd:
            return passwd

        return format_html(f'<div title="{passwd}">******</div>')


@admin.register(ServerServiceTimedStats)
class ServerServiceTimedStatsAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'show_time', 'server_count', 'disk_count', 'ip_count',
                    'ip_used_count', 'pub_ip_count', 'pub_ip_used_count', 'pri_ip_count', 'pri_ip_used_count',
                    'mem_size', 'mem_used_size', 'cpu_count', 'cpu_used_count')
    list_filter = ['service']
    list_select_related = ('service',)
    raw_id_fields = ('service',)

    @admin.display(description=gettext_lazy("统计时间"))
    def show_time(self, obj):
        try:
            dt = datetime.fromtimestamp(obj.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            return ''

        return dt.isoformat(sep=' ')


@admin.register(VPNTimedStats)
class VPNTimedStatsAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'show_time', 'vpn_online_count', 'vpn_active_count', 'vpn_count')
    list_filter = ['service']
    list_select_related = ('service',)
    raw_id_fields = ('service',)

    @admin.display(description=gettext_lazy("统计时间"))
    def show_time(self, obj):
        try:
            dt = datetime.fromtimestamp(obj.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            return ''

        return dt.isoformat(sep=' ')


@admin.register(ObjectServiceTimedStats)
class ObjectServiceTimedStatsAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'show_time', 'bucket_count', 'bucket_storage', 'storage_used', 'storage_capacity')
    list_filter = ['service']
    list_select_related = ('service',)
    raw_id_fields = ('service',)

    @admin.display(description=gettext_lazy("统计时间"))
    def show_time(self, obj):
        try:
            dt = datetime.fromtimestamp(obj.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            return ''

        return dt.isoformat(sep=' ')


@admin.register(ObjectServiceLog)
class ObjectServiceLogAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'username', 'content', 'creation_time', 'create_time')
    search_fields = ['username', 'content']
    list_filter = ['service_cell']


@admin.register(ServerServiceLog)
class ServerServiceLogAdmin(BaseModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'username', 'content', 'creation_time', 'create_time')
    search_fields = ['username', 'content']
    list_filter = ['service_cell']


@admin.register(HostNetflow)
class HostNetflowAdmin(BaseModelAdmin):
    list_display = ('id', 'timestamp', 'show_time', 'unit', 'flow_in', 'flow_out')
    list_display_links = ('id',)
    list_select_related = ('unit',)

    @admin.display(description=gettext_lazy("统计时间"))
    def show_time(self, obj):
        try:
            dt = datetime.fromtimestamp(obj.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            return ''

        return dt.isoformat(sep=' ')


class WebsiteMonitorTaskForm(forms.ModelForm):
    def clean(self):
        try:
            ScreenWebMonitorManager.get_check_task_configs()
        except Exception as exc:
            raise ValidationError(message=str(exc))

        return super().clean()


@admin.register(WebsiteMonitorTask)
class WebsiteMonitorTaskAdmin(NoDeleteSelectModelAdmin):
    form = WebsiteMonitorTaskForm
    list_display = ('id', 'name', 'url', 'url_hash', 'is_tamper_resistant', 'creation_time')
    list_display_links = ('id',)
    search_fields = ('url',)
    readonly_fields = ('url_hash',)

    def save_model(self, request, obj, form, change):
        obj: WebsiteMonitorTask
        if change:
            old_obj = WebsiteMonitorTask.objects.get(id=obj.id)
            if old_obj.url != obj.url or old_obj.is_tamper_resistant != obj.is_tamper_resistant:
                obj.reset_url_hash()
                try:
                    ScreenWebMonitorManager.change_task_to_probe(
                        web_url=old_obj.url, url_hash=old_obj.url_hash, is_tamper_resistant=old_obj.is_tamper_resistant,
                        new_web_url=obj.url, new_url_hash=obj.url_hash, new_is_tamper_resistant=obj.is_tamper_resistant
                    )
                except Exception as exc:
                    self.message_user(request, gettext("修改监控任务失败，任务变更推送到探针失败。") + str(exc),
                                      level=messages.ERROR)
                    request.post_to_probe_failed = True
                    return

                self.message_user(request, gettext("监控任务变更成功推送到探针"), level=messages.SUCCESS)
        else:
            obj.reset_url_hash()
            try:
                ScreenWebMonitorManager.add_task_to_probe(
                    web_url=obj.url, url_hash=obj.url_hash, is_tamper_resistant=obj.is_tamper_resistant)
            except Exception as exc:
                self.message_user(request, gettext("添加监控任务失败，新任务推送到探针失败。") + str(exc),
                                  level=messages.ERROR)
                request.post_to_probe_failed = True
                return

            self.message_user(request, gettext("新监控任务成功推送到探针"), level=messages.SUCCESS)

        super().save_model(request=request, obj=obj, form=form, change=change)

    def response_change(self, request, obj):
        r = super(WebsiteMonitorTaskAdmin, self).response_change(request=request, obj=obj)
        self.remove_success_messages_when_failed(request=request, response=r)
        return r

    def response_add(self, request, obj, post_url_continue=None):
        r = super(WebsiteMonitorTaskAdmin, self).response_add(request=request, obj=obj)
        self.remove_success_messages_when_failed(request=request, response=r)
        return r

    @staticmethod
    def remove_success_messages_when_failed(request, response):
        post_to_probe_failed = getattr(request, 'post_to_probe_failed', False)
        if not post_to_probe_failed:
            return response

        storage = messages.get_messages(request)
        msgs = []
        for m in storage:
            if m.level == messages.SUCCESS:
                continue

            msgs.append(m)

        for m in msgs:
            messages.add_message(request, m.level, m.message)

        return response

    def delete_model(self, request, obj):
        try:
            ScreenWebMonitorManager.remove_task_from_probe(
                web_url=obj.url, url_hash=obj.url_hash, is_tamper_resistant=obj.is_tamper_resistant)
        except Exception as exc:
            self.message_user(request, gettext("删除监控任务失败，从探针删除任务失败。") + str(exc),
                              level=messages.ERROR)
            request.post_to_probe_failed = True
            return

        super().delete_model(request=request, obj=obj)
        self.message_user(request, gettext("成功从探针删除监控任务"), level=messages.SUCCESS)

    def response_delete(self, request, obj_display, obj_id):
        r = super(WebsiteMonitorTaskAdmin, self).response_delete(
            request=request, obj_display=obj_display, obj_id=obj_id)
        self.remove_success_messages_when_failed(request=request, response=r)
        return r
