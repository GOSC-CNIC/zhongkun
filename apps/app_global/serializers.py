from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class AnnouncementSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    name = serializers.CharField(label=_('标题'), max_length=128)
    name_en = serializers.CharField(label=_('英文标题'), max_length=128)
    status = serializers.CharField(label=_('状态'), max_length=16)
    content = serializers.CharField(label=_('内容'))
    content_en = serializers.CharField(label=_('英文内容'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    expire_time = serializers.DateTimeField(label=_('过期时间'))
    publisher = serializers.SerializerMethodField(method_name='get_publisher')

    @staticmethod
    def get_publisher(obj):
        publisher = obj.publisher
        if publisher is None:
            return None

        return {'id': publisher.id, 'username': publisher.username}
