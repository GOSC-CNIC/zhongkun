from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class LinkOrgSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    name = serializers.CharField(max_length=64, label=_('二级机构名'), allow_blank=False, allow_null=False, required=True)
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    location = serializers.CharField(label=_('经纬度'), max_length=64, allow_blank=True, allow_null=True, required=False, default='')
    data_center = serializers.SerializerMethodField(label=_('数据中心'), method_name='get_data_center')

    @staticmethod
    def get_data_center(obj):
        data_center = obj.data_center
        if data_center is not None:
            return {'id': data_center.id, 'name': data_center.name, 'name_en': data_center.name_en}
        return None
    