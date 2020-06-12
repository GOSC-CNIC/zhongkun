from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ServerSerializer(serializers.Serializer):
    """
    虚拟服务器实例序列化器
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    vcpus = serializers.IntegerField()
    ram = serializers.IntegerField()
    ipv4 = serializers.CharField()
    image = serializers.CharField()
    creation_time = serializers.DateTimeField()
    remarks = serializers.CharField()


class ServerCreateSerializer(serializers.Serializer):
    """
    创建虚拟服务器序列化器
    """
    service_id = serializers.IntegerField(label=_('服务'), required=True, min_value=1, help_text=_('服务提供商配置ID'))
    image_id = serializers.CharField(label=_('镜像id'), required=True, help_text=_('系统镜像id'))
    flavor_id = serializers.CharField(label=_('配置样式id'), required=True, help_text=_('硬件配置样式ID'))
    network_id = serializers.CharField(label=_('子网id'), required=False, default='', help_text=_('子网ID'))
    remarks = serializers.CharField(label=_('备注'), required=False, allow_blank=True, max_length=255, default='')

    def validate(self, attrs):
        return attrs


class VPNSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    password = serializers.CharField()
    created_time = serializers.DateTimeField()  # format='%Y-%m-%d %H:%M:%S'
    modified_time = serializers.DateTimeField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        u = obj.user
        return {'id': u.id, 'username': u.username}


class VPNPostSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=20, min_length=6, help_text=_('新的VPN口令密码'))
