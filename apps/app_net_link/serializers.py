from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from rest_framework import serializers


class NetLinkUserRoleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    is_link_admin = serializers.BooleanField(
        label=_('链路管理员'), default=False, help_text=_('选中，用户拥有链路管理功能的管理员权限'))
    is_link_readonly = serializers.BooleanField(
        label=_('链路管理全局只读权限'), default=False, help_text=_('选中，用户拥有链路管理功能的全局只读权限'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user = serializers.SerializerMethodField(label=_('用户'), method_name='get_user')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None


class ElementBaseSerializer(serializers.Serializer):
    is_linked = serializers.BooleanField(label=_('接入链路'), read_only=True)
    element_id = serializers.CharField(label=_('网元ID'), max_length=36, read_only=True)
    link_id = serializers.ListField(
        label=_('链路ID数组'), read_only=True, child=serializers.CharField(label=_('链路ID'), max_length=36))


class ConnectorBoxSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('接头盒编号'), allow_blank=False, allow_null=False, required=True)
    place = serializers.CharField(
        label=_('位置'), max_length=128, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(
        label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    location = serializers.CharField(
        label=_('经纬度'), max_length=64, allow_blank=True, allow_null=True, required=False, default='')


class DistriFrameSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('设备号'), required=True)
    model_type = serializers.CharField(max_length=36, label=_('设备型号'), required=True)
    row_count = serializers.IntegerField(label=_('行数'), validators=(MinValueValidator(1),), required=True)
    col_count = serializers.IntegerField(label=_('列数'), validators=(MinValueValidator(1),), required=True)
    place = serializers.CharField(label=_('位置'), max_length=128, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    link_org = serializers.SerializerMethodField(label=_('机构二级'), method_name='get_link_org')

    @staticmethod
    def get_link_org(obj):
        link_org = obj.link_org
        if link_org is not None:
            return {'id': link_org.id, 'name': link_org.name}

        return None


class DistriFramePortSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('端口编号'), required=True)
    row = serializers.IntegerField(label=_('行号'), validators=(MinValueValidator(1),), required=True)
    col = serializers.IntegerField(label=_('列号'), validators=(MinValueValidator(1),), required=True)
    distribution_frame = serializers.SerializerMethodField(label=_('配线架'), method_name='get_distribution_frame')

    @staticmethod
    def get_distribution_frame(obj):
        distribution_frame = obj.distribution_frame
        if distribution_frame is not None:
            return {'id': distribution_frame.id, 'number': distribution_frame.number}

        return None


class FiberCableSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('光缆编号'), required=True)
    fiber_count = serializers.IntegerField(label=_('总纤芯数量'), validators=(MinValueValidator(0),), required=True)
    length = serializers.DecimalField(
        label=_('长度'), validators=(MinValueValidator(0),),  max_digits=10, decimal_places=2, required=True)
    endpoint_1 = serializers.CharField(
        label=_('端点1'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    endpoint_2 = serializers.CharField(
        label=_('端点2'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(
        label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')


class LeaseLineSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    private_line_number = serializers.CharField(max_length=64, label=_('专线号'), required=True)
    lease_line_code = serializers.CharField(
        max_length=64, label=_('电路代号'), default='', allow_blank=True, allow_null=True, required=False)
    line_username = serializers.CharField(
        max_length=36, label=_('用户'), default='', allow_blank=True, allow_null=True, required=False)
    endpoint_a = serializers.CharField(
        max_length=255, label=_('A端'), default='', allow_blank=True, allow_null=True, required=False)
    endpoint_z = serializers.CharField(
        max_length=255, label=_('Z端'), default='', allow_blank=True, allow_null=True, required=False)
    line_type = serializers.CharField(
        max_length=36, label=_('线路类型'), default='', allow_blank=True, allow_null=True, required=False)
    cable_type = serializers.CharField(
        max_length=36, label=_('电路类型'), default='', allow_blank=True, allow_null=True, required=False)
    bandwidth = serializers.IntegerField(
        label=_('带宽'), validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    length = serializers.DecimalField(
        label=_('长度'), max_digits=10, decimal_places=2, validators=(MinValueValidator(0),), default=None,
        allow_null=True, required=False)
    provider = serializers.CharField(
        max_length=36, label=_('运营商'), default='', allow_blank=True, allow_null=True, required=False)
    enable_date = serializers.DateField(label=_('开通日期'), default=None, allow_null=True, required=False)
    is_whithdrawal = serializers.BooleanField(label=_('租线状态'), allow_null=False, required=True)
    money = serializers.DecimalField(
        label=_('月租费'), validators=(MinValueValidator(0),), max_digits=10, decimal_places=2,
        default=None, allow_null=True, required=False)
    remarks = serializers.CharField(
        max_length=255, label=_('备注'), default='', allow_blank=True, allow_null=True, required=False)


class OpticalFiberSerializer(ElementBaseSerializer):
    id = serializers.CharField(label='ID', max_length=36, read_only=True)
    sequence = serializers.IntegerField(label=_('纤序'), read_only=True)
    fiber_cable = serializers.SerializerMethodField(label=_('光缆'), method_name='get_fibercable')

    @staticmethod
    def get_fibercable(obj):
        fibercable = obj.fiber_cable
        if fibercable is not None:
            return {'id': fibercable.id, 'number': fibercable.number}

        return None


class ElementDetailDataSerializer(serializers.Serializer):
    """网元详情列化器"""
    type = serializers.CharField(max_length=32, label='网元类型', read_only=True)
    lease = LeaseLineSerializer()
    port = DistriFramePortSerializer()
    fiber = OpticalFiberSerializer()
    box = ConnectorBoxSerializer()


class LinkSerializer(serializers.Serializer):
    """链路基本信息列化器"""
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=128, label=_('业务编号'), allow_blank=False, allow_null=False, required=True)
    user = serializers.CharField(max_length=128, label=_('用户'), allow_blank=False, allow_null=False, required=True)
    endpoint_a = serializers.CharField(max_length=255, label=_('A端'), allow_blank=False, allow_null=False, required=True)
    endpoint_z = serializers.CharField(max_length=255, label=_('Z端'), allow_blank=False, allow_null=False, required=True)
    bandwidth = serializers.IntegerField(
        label=_('带宽'), validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    description = serializers.CharField(max_length=255, label=_('用途描述'), allow_blank=False, allow_null=False, required=True)
    line_type = serializers.CharField(max_length=36, label=_('线路类型'), allow_blank=False, allow_null=False, required=True)
    business_person = serializers.CharField(max_length=36, label=_('商务对接'), allow_blank=False, allow_null=False, required=True)
    build_person = serializers.CharField(max_length=36, label=_('线路搭建'), allow_blank=False, allow_null=False, required=True)
    link_status = serializers.CharField(max_length=16, label=_('链路状态'), allow_blank=False, allow_null=False, required=True)
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    enable_date = serializers.DateField(label=_('开通日期'), default=None, allow_null=True, required=False)


class LinkElementSerializer(serializers.Serializer):
    """链路网元关系列化器"""
    index = serializers.IntegerField(label=_('链路位置'), validators=(MinValueValidator(1),))
    sub_index = serializers.IntegerField(label=_('同位编号'), validators=(MinValueValidator(1),))
    element_data = ElementDetailDataSerializer()


class LinkDetailSerializer(LinkSerializer):
    """链路详情（链路基本信息，网元信息）序列化器"""
    link_element = LinkElementSerializer(many=True)


class CreatLinkElementSerializer(serializers.Serializer):
    """创建链路网元关系序列化器"""
    index = serializers.IntegerField(label=_('链路位置'), validators=(MinValueValidator(1),), required=True)
    sub_index = serializers.IntegerField(
        label=_('同位编号'), validators=(MinValueValidator(1),), default=1, allow_null=True, required=False)
    element_id = serializers.CharField(max_length=36, label=_('网元id'), required=True)


class CreatLinkSerializer(LinkSerializer):
    """创建链路序列化器"""
    link_element = CreatLinkElementSerializer(many=True, required=True)
