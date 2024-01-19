from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator
from link.serializers.element_serializer import ElementBaseSerializer

class DistriFramePortSerializer(ElementBaseSerializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('端口编号'), allow_blank=False, allow_null=False, required=True)
    row = serializers.IntegerField(label=_('行号'), validators=(MinValueValidator(1),), allow_null=False, required=True)
    col = serializers.IntegerField(label=_('列号'), validators=(MinValueValidator(1),), allow_null=False, required=True)
    distribution_frame = serializers.SerializerMethodField(label=_('配线架'), method_name='get_distribution_frame')

    class Meta:
        ref_name = 'link'  # 在线文档 drf-yasg 需要区分同名的 Serializer

    @staticmethod
    def get_distribution_frame(obj):
        distribution_frame = obj.distribution_frame
        if distribution_frame is not None:
            return {'id': distribution_frame.id, 'number': distribution_frame.number}

        return None

