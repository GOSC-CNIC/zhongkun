from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class VoSerializer(serializers.Serializer):
    id = serializers.CharField(
        label=_('组ID'), read_only=True)
    name = serializers.CharField(label=_('组名称'), max_length=255, required=True)
    company = serializers.CharField(label=_('工作单位'), max_length=256, required=True)
    description = serializers.CharField(label=_('组描述'), max_length=1024, required=True)

    creation_time = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    owner = serializers.SerializerMethodField(label=_('所有者'), method_name='get_owner', read_only=True)
    status = serializers.CharField(label=_('状态'), read_only=True)

    @staticmethod
    def get_owner(obj):
        if obj.owner:
            return {'id': obj.owner.id, 'username': obj.owner.username}

        return None


class VoUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('组名称'), max_length=255, required=False, allow_null=True)
    company = serializers.CharField(label=_('单位'), max_length=256, required=False, allow_null=True)
    description = serializers.CharField(label=_('组描述'), max_length=1024, required=False, allow_null=True)


class VoMembersAddSerializer(serializers.Serializer):
    usernames = serializers.ListField(label=_('用户名'), max_length=1000, required=True, allow_null=False,
                                      allow_empty=False)


class VoMemberSerializer(serializers.Serializer):
    id = serializers.CharField(label='id', read_only=True)
    user = serializers.SerializerMethodField(label=_('用户'), read_only=True)
    # vo = serializers.SerializerMethodField(label=_('用户'), read_only=True)
    role = serializers.CharField(label=_('组员角色'), read_only=True)
    join_time = serializers.DateTimeField(label=_('加入时间'), read_only=True)
    inviter = serializers.CharField(label=_('邀请人'), max_length=256, read_only=True)

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None
