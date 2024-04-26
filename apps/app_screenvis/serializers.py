from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.app_screenvis.models import DataCenter


def get_data_center_dict(odc: DataCenter):
    if odc is None:
        return None

    data = {
        'id': odc.id, 'name': odc.name, 'name_en': odc.name_en, 'sort_weight': odc.sort_weight
    }

    return data


class DataCenterSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    name = serializers.CharField(label=_('名称'))
    name_en = serializers.CharField(label=_('英文名称'))
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))
    sort_weight = serializers.IntegerField(label=_('排序值'), help_text=_('值越小排序越靠前'))
    remark = serializers.CharField(label=_('数据中心备注'))


class MetricMntrUnitSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('指标单元id'))
    name = serializers.CharField(label=_('名称'))
    name_en = serializers.CharField(label=_('英文名称'))
    unit_type = serializers.CharField(label=_('指标单元类型'))
    job_tag = serializers.CharField(label=_('标签名称'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class MetricMntrUnitSerializer(MetricMntrUnitSimpleSerializer):
    """ceph监控单元"""
    remark = serializers.CharField(label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序权重'), help_text=_('值越大排序越靠前'))
    grafana_url = serializers.CharField(label=_('Grafana连接'), max_length=255)
    dashboard_url = serializers.CharField(label=_('Dashboard连接'), max_length=255)
    data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_data_center')

    @staticmethod
    def get_data_center(obj):
        return get_data_center_dict(obj.data_center)


class LogMntrUnitSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    name = serializers.CharField(label=_("日志单元名称"))
    name_en = serializers.CharField(label=_('日志单元英文名称'))
    log_type = serializers.CharField(label=_("日志类型"))
    job_tag = serializers.CharField(label=_('日志单元标识'))
    sort_weight = serializers.IntegerField(label=_('排序值'), help_text=_('值越小排序越靠前'))
    remark = serializers.CharField(label=_("备注"))
    data_center = serializers.SerializerMethodField(label=_('数据中心'), method_name='get_data_center')

    @staticmethod
    def get_data_center(obj):
        return get_data_center_dict(obj.data_center)


class BaseServiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255, label=_('服务名称'))
    name_en = serializers.CharField(label=_('服务英文名称'), max_length=255)
    endpoint_url = serializers.CharField(max_length=255, label=_('服务地址url'))
    status = serializers.CharField(label=_('服务状态'), max_length=32)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序值'), help_text=_('值越小排序越靠前'))
    data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_data_center')

    @staticmethod
    def get_data_center(obj):
        return get_data_center_dict(obj.data_center)


class ServiceUserOperateLogSerializer(serializers.Serializer):
    creation_time = serializers.DateTimeField()
    username = serializers.CharField()
    content = serializers.CharField()