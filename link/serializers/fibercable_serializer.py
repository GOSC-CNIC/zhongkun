from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator
from link.serializers.element_serializer import ElementBaseSerializer

class FiberCableSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('光缆编号'), allow_blank=False, allow_null=False, required=True)
    fiber_count = serializers.IntegerField(label=_('总纤芯数量'), validators=(MinValueValidator(0),), allow_null=False, required=True)
    length = serializers.DecimalField(label=_('长度'), validators=(MinValueValidator(0),),  max_digits=10, decimal_places=2, allow_null=False, required=True)
    endpoint_1 = serializers.CharField(label=_('端点1'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    endpoint_2 = serializers.CharField(label=_('端点2'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')

    class Meta:
        ref_name = 'link'   # 在线文档 drf-yasg 需要区分同名的 Serializer
