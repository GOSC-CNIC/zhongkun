from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class DataCenterSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    abbreviation = serializers.CharField()
    creation_time = serializers.DateTimeField()
    status = serializers.SerializerMethodField(method_name='get_status')
    desc = serializers.CharField()
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    sort_weight = serializers.IntegerField()

    @staticmethod
    def get_status(obj):
        s = obj.status
        if s is None:
            return {'code': None, 'message': None}

        return {'code': s, 'message': obj.get_status_display()}


class UserSerializer(serializers.Serializer):
    """
    用户
    """
    id = serializers.CharField(label=_('ID'), read_only=True)
    username = serializers.CharField(label=_('用户名'))
    fullname = serializers.SerializerMethodField(method_name='get_fullname')
    role = serializers.SerializerMethodField(label=_('角色'), method_name='get_role')
    is_fed_admin = serializers.BooleanField(label=_('联邦管理员'))

    @staticmethod
    def get_fullname(obj):
        return obj.get_full_name()

    @staticmethod
    def get_role(obj):
        roles = []
        if obj.is_fed_admin:
            roles.append('federal-admin')

        return {
            "role": roles
        }
