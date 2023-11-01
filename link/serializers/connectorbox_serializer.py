from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from link.serializers.element_serializer import ElementBaseSerializer

class ConnectorBoxSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('接头盒编号'), allow_blank=False, allow_null=False, required=True)
    place = serializers.CharField(label=_('位置'), max_length=128, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    location = serializers.CharField(label=_('经纬度'), max_length=64, allow_blank=True, allow_null=True, required=False, default='')