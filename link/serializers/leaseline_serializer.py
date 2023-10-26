from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator
from link.serializers.element_serializer import ElementBaseSerializer

class LeaseLineSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    private_line_number = serializers.CharField(max_length=64, label=_('专线号'), allow_blank=True, allow_null=False, required=True)
    lease_line_code = serializers.CharField(max_length=64, label=_('电路代号'), default='', allow_blank=True, allow_null=True, required=False)
    line_username = serializers.CharField(max_length=36, label=_('用户'), default='', allow_blank=True, allow_null=True, required=False)
    endpoint_a = serializers.CharField(max_length=255, label=_('A端'), default='', allow_blank=True, allow_null=True, required=False)
    endpoint_z = serializers.CharField(max_length=255, label=_('Z端'), default='', allow_blank=True, allow_null=True, required=False)
    line_type = serializers.CharField(max_length=36, label=_('线路类型'), default='', allow_blank=True, allow_null=True, required=False)
    cable_type = serializers.CharField(max_length=36, label=_('电路类型'), default='', allow_blank=True, allow_null=True, required=False)
    bandwidth = serializers.IntegerField(label=_('带宽'), validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    length = serializers.DecimalField(label=_('长度'), max_digits=10, decimal_places=2, validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    provider = serializers.CharField(max_length=36, label=_('运营商'), default='', allow_blank=True, allow_null=True, required=False)
    enable_date = serializers.DateField(label=_('开通日期'), default=None, allow_null=True, required=False)
    is_whithdrawal = serializers.BooleanField(label=_('租线状态'), allow_null=False, required=True)
    money = serializers.DecimalField(label=_('月租费'), validators=(MinValueValidator(0),), max_digits=10, decimal_places=2, default=None, allow_null=True, required=False)
    remarks = serializers.CharField(max_length=255, label=_('备注'), default='', allow_blank=True, allow_null=True, required=False)
