from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator
from link.serializers.leaseline_serializer import LeaseLineSerializer
from link.serializers.connectorbox_serializer import ConnectorBoxSerializer
from link.serializers.opticalfiber_serializer import OpticalFiberSerializer
from link.serializers.distriframeport_serializer import DistriFramePortSerializer

class ElementDetailDataSerializer(serializers.Serializer):
    """网元详情列化器"""
    type = serializers.CharField(max_length=32, label='网元类型', read_only=True)
    lease = LeaseLineSerializer()
    port = DistriFramePortSerializer()
    fiber = OpticalFiberSerializer()
    box = ConnectorBoxSerializer()

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class LinkSerializer(serializers.Serializer):
    """链路基本信息列化器"""
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=128, label=_('业务编号'), allow_blank=False, allow_null=False, required=True)
    user = serializers.CharField(max_length=128, label=_('用户'), allow_blank=False, allow_null=False, required=True)
    endpoint_a = serializers.CharField(max_length=255, label=_('A端'), allow_blank=False, allow_null=False, required=True)
    endpoint_z = serializers.CharField(max_length=255, label=_('Z端'), allow_blank=False, allow_null=False, required=True)
    bandwidth = serializers.IntegerField(label=_('带宽'), validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    description = serializers.CharField(max_length=255, label=_('用途描述'), allow_blank=False, allow_null=False, required=True)
    line_type = serializers.CharField(max_length=36, label=_('线路类型'), allow_blank=False, allow_null=False, required=True)
    business_person = serializers.CharField(max_length=36, label=_('商务对接'), allow_blank=False, allow_null=False, required=True)
    build_person = serializers.CharField(max_length=36, label=_('线路搭建'), allow_blank=False, allow_null=False, required=True)
    link_status = serializers.CharField(max_length=16, label=_('链路状态'), allow_blank=False, allow_null=False, required=True)
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    enable_date = serializers.DateField(label=_('开通日期'), default=None, allow_null=True, required=False)

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class LinkElementSerializer(serializers.Serializer):
    """链路网元关系列化器"""
    index = serializers.IntegerField(label=_('链路位置'), validators=(MinValueValidator(1),))
    sub_index = serializers.IntegerField(label=_('同位编号'), validators=(MinValueValidator(1),))
    element_data = ElementDetailDataSerializer()

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class LinkDetailSerializer(LinkSerializer):
    """链路详情（链路基本信息，网元信息）序列化器"""
    link_element = LinkElementSerializer(many=True)

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class CreatLinkElementSerializer(serializers.Serializer):
    """创建链路网元关系序列化器"""
    index = serializers.IntegerField(label=_('链路位置'), validators=(MinValueValidator(1),), required=True)
    sub_index = serializers.IntegerField(label=_('同位编号'), validators=(MinValueValidator(1),), default=1, allow_null=True, required=False)
    element_id = serializers.CharField(max_length=36, label=_('网元id'), required=True)

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class CreatLinkSerializer(LinkSerializer):
    """创建链路序列化器"""
    link_element = CreatLinkElementSerializer(many=True, required=True)

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer

