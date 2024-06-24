from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


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


class BaseServiceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(max_length=255, label=_('服务名称'))
    name_en = serializers.CharField(label=_('服务英文名称'), max_length=255)
    endpoint_url = serializers.CharField(max_length=255, label=_('服务地址url'))
    status = serializers.CharField(label=_('服务状态'), max_length=32)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序值'), help_text=_('值越小排序越靠前'))


class ServiceUserOperateLogSerializer(serializers.Serializer):
    creation_time = serializers.DateTimeField()
    username = serializers.CharField()
    content = serializers.CharField()


class AlertSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(max_length=100, label=_('名称'))
    type = serializers.CharField(max_length=64, label=_('类型'))
    instance = serializers.CharField(max_length=100, label=_('告警实例'))
    port = serializers.CharField(max_length=100, label=_('告警端口'))
    cluster = serializers.CharField(max_length=50, label=_('集群名称'))
    severity = serializers.CharField(max_length=50, label=_('级别'))
    summary = serializers.CharField(label=_('摘要'))
    description = serializers.CharField(label=_('详情'))
    start = serializers.IntegerField(label=_('告警开始时间'))
    end = serializers.IntegerField(label=_('告警预结束时间'))
    status = serializers.CharField(max_length=20, label=_("告警状态"))
    count = serializers.IntegerField(label=_('累加条数'))
    creation = serializers.FloatField(label=_('创建时间'))
    # modification = serializers.IntegerField(label=_('更新时间'))
