from datetime import datetime

from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy
from django.utils import timezone as dj_timezone
from django.utils.html import format_html


from utils.model import BaseModelAdmin
from .models import (
    ScreenConfig, DataCenter, MetricMonitorUnit, LogMonitorUnit, HostCpuUsage,
    ServerService, ObjectService, ServerServiceTimedStats, ObjectServiceTimedStats, VPNTimedStats,
    ObjectServiceLog, ServerServiceLog, HostNetflow
)


@admin.register(ScreenConfig)
class ScreenConfigAdmin(BaseModelAdmin):
    list_display_links = ('id', 'name')
    list_display = ('id', 'name', 'value', 'creation_time', 'remark')
    search_fields = ('name', 'value')


@admin.register(DataCenter)
class DataCenterAdmin(BaseModelAdmin):
    list_display_links = ('id', 'name')
    list_display = ('id', 'name', 'name_en', 'sort_weight', 'longitude', 'latitude',
                    'creation_time', 'update_time',
                    'metric_endpoint_url', 'metric_receive_url', 'loki_endpoint_url', 'loki_receive_url')
    search_fields = ['name', 'name_en', 'remark']
    list_editable = ('sort_weight',)
    fieldsets = (
        (gettext_lazy('数据中心基础信息'), {
            'fields': (
                'name', 'name_en', 'sort_weight', 'longitude', 'latitude', 'remark',
                'creation_time', 'update_time'
            )
        }),
        (gettext_lazy('指标监控系统'), {
            'fields': (
                'metric_endpoint_url', 'metric_receive_url', 'metric_remark',
            )
        }),
        (gettext_lazy('日志聚合系统'), {
            'fields': (
                'loki_endpoint_url', 'loki_receive_url', 'loki_remark'
            )
        }),
    )


@admin.register(MetricMonitorUnit)
class MetricMonitorUnitAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'name_en', 'unit_type', 'data_center', 'sort_weight',
                    'job_tag', 'metric_endpoint_url', 'prometheus', 'creation_time', 'update_time')
    list_display_links = ('id', 'name')
    list_select_related = ('data_center', )
    list_editable = ('sort_weight',)
    list_filter = ('data_center',)
    search_fields = ('name', 'name_en', 'job_tag',)
    raw_id_fields = ('data_center',)

    @admin.display(description=gettext_lazy("指标监控系统url"))
    def metric_endpoint_url(self, obj):
        if not obj.data_center:
            return ''

        return obj.data_center.metric_endpoint_url


# @admin.register(LogMonitorUnit)
class LogMonitorUnitAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'name_en', 'log_type', 'data_center', 'sort_weight',
                    'job_tag', 'loki_endpoint_url', 'creation_time', 'update_time')
    list_display_links = ('id', 'name')
    list_select_related = ('data_center', )
    list_editable = ('sort_weight',)
    list_filter = ('log_type', 'data_center',)
    raw_id_fields = ('data_center',)
    search_fields = ('name', 'name_en', 'job_tag',)

    @admin.display(description=gettext_lazy("日志聚合系统url"))
    def loki_endpoint_url(self, obj):
        if not obj.data_center:
            return ''

        return obj.data_center.loki_endpoint_url


@admin.register(HostCpuUsage)
class HostCpuUsageAdmin(BaseModelAdmin):
    list_display = ('id', 'timestamp', 'show_time', 'unit', 'value')
    list_display_links = ('id',)
    list_select_related = ('unit',)

    @admin.display(description=gettext_lazy("统计时间"))
    def show_time(self, obj):
        try:
            dt = datetime.fromtimestamp(obj.timestamp, tz=dj_timezone.get_default_timezone())
        except Exception as exc:
            return ''

        return dt.isoformat(sep=' ')


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
    list_display = ('id', 'name', 'name_en', 'data_center', 'status', 'sort_weight', 'endpoint_url',
                    'username', 'password', 'raw_password', 'creation_time', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['data_center']
    list_select_related = ('data_center',)
    raw_id_fields = ('data_center',)
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
    list_display = ('id', 'name', 'name_en', 'data_center', 'status', 'sort_weight', 'endpoint_url',
                    'username', 'password', 'raw_password', 'creation_time', 'remarks')
    search_fields = ['name', 'name_en', 'endpoint_url', 'remarks']
    list_filter = ['data_center']
    list_select_related = ('data_center',)
    raw_id_fields = ('data_center',)
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
                    'ip_used_count', 'mem_size', 'mem_used_size', 'cpu_count', 'cpu_used_count')
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
