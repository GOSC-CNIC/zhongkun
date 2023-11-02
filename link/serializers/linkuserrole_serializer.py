from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class LinkUserRoleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    is_admin = serializers.BooleanField(
        label=_('科技网链路管理员'), default=False, help_text=_('选中，用户拥有科技网链路管理功能的管理员权限'))
    is_readonly = serializers.BooleanField(
        label=_('链路管理全局只读权限'), default=False, help_text=_('选中，用户拥有科技网链路管理功能的全局只读权限'))
    create_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user = serializers.SerializerMethodField(label=_('用户'), method_name='get_user')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None