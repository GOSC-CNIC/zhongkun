from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .serializers import get_org_data_center_dict


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
    site_type = LogSiteTypeSerializer(allow_null=True)
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')

    @staticmethod
    def get_org_data_center(obj):
        return get_org_data_center_dict(obj.org_data_center)
