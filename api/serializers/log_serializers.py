from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .monitor import MonitorOrganizationSimpleSerializer


class LogSiteTypeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(label="日志网站类别名称")
    name_en = serializers.CharField(label=_('英文名称'))
    sort_weight = serializers.IntegerField(label='排序值', help_text='值越小排序越靠前')
    desc = serializers.CharField(label="备注")


class LogSiteSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(label="日志单元名称")
    name_en = serializers.CharField(label=_('日志单元英文名称'))
    log_type = serializers.CharField(label="日志类型")
    job_tag = serializers.CharField(label=_('网站日志单元标识'))
    sort_weight = serializers.IntegerField(label='排序值', help_text='值越小排序越靠前')
    desc = serializers.CharField(label="备注")
    creation = serializers.DateTimeField(label='创建时间')
    organization = MonitorOrganizationSimpleSerializer(required=False, allow_null=True)
    site_type = LogSiteTypeSerializer(allow_null=True)
