from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class UserSerializer(serializers.Serializer):
    """
    用户
    """
    id = serializers.CharField(label=_('ID'), read_only=True)
    username = serializers.CharField(label=_('用户名'))
    fullname = serializers.SerializerMethodField(method_name='get_fullname')
    is_fed_admin = serializers.BooleanField(label=_('联邦管理员'))
    organization = serializers.SerializerMethodField(label=_('机构'), method_name='get_organization')

    @staticmethod
    def get_fullname(obj):
        return obj.get_full_name()

    @staticmethod
    def get_organization(obj):
        org = obj.organization
        if not org:
            return None

        return {
            'id': org.id, 'name': org.name, 'name_en': org.name_en
        }

