from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class DiskCreateSerializer(serializers.Serializer):
    """
    创建云硬盘序列化器
    """
    pay_type = serializers.CharField(label=_('付费模式'), required=True, max_length=16)
    service_id = serializers.CharField(label=_('服务单元'), required=True, help_text=_('服务提供商配置ID'))
    azone_id = serializers.CharField(label=_('可用区'), required=True, max_length=36)
    size = serializers.IntegerField(label=_('云盘大小（GiB）'), min_value=1, max_value=10240, required=True)
    period = serializers.IntegerField(
        label=_('订购时长（月）'), required=False, allow_null=True, default=None,
        help_text=_('付费模式为预付费时，必须指定订购时长'))
    remarks = serializers.CharField(label=_('备注'), required=False, allow_blank=True, max_length=255, default='')
    vo_id = serializers.CharField(
        label=_('vo组id'), required=False, allow_null=True, max_length=36, default=None,
        help_text=_('通过vo_id指定为vo组创建云服务器'))
