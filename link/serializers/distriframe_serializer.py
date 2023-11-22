from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator

class DistriFrameSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('设备号'), allow_blank=False, allow_null=False, required=True)
    model_type = serializers.CharField(max_length=36, label=_('设备型号'), allow_blank=False, allow_null=False, required=True)
    row_count = serializers.IntegerField(label=_('行数'), validators=(MinValueValidator(1),), allow_null=False, required=True)
    col_count = serializers.IntegerField(label=_('列数'), validators=(MinValueValidator(1),), allow_null=False, required=True)
    place = serializers.CharField(label=_('位置'), max_length=128, allow_blank=True, allow_null=True, required=False, default='')
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    link_org = serializers.SerializerMethodField(label=_('机构二级'), method_name='get_link_org')

    @staticmethod
    def get_link_org(obj):
        link_org = obj.link_org
        if link_org is not None:
            return {'id': link_org.id, 'name': link_org.name}
        return None

