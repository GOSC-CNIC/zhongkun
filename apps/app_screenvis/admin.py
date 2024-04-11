from datetime import datetime

from django.utils import timezone as dj_timezone
from django.contrib import admin
from django.utils.translation import gettext_lazy

from utils.model import BaseModelAdmin
from .models import ScreenConfig, DataCenter, MetricMonitorUnit, LogMonitorUnit, HostCpuUsage


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


@admin.register(LogMonitorUnit)
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
