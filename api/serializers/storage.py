from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class BucketCreateSerializer(serializers.Serializer):
    service_id = serializers.CharField(label=_('服务单元ID'), max_length=36, required=True)
    name = serializers.CharField(label=_('存储桶名称'), max_length=73, required=True)


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('存储桶ID'))
    name = serializers.CharField(label=_('存储桶名称'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户id'))
    service = serializers.SerializerMethodField(method_name='get_service')

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

        return {'id': None, 'name': None, 'name_en': None}
