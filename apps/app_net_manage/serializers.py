from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class NetManageUserRoleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    role = serializers.CharField()
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user = serializers.SerializerMethodField(label=_('用户'), method_name='get_user')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None


class OrgVirtualObjectSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    name = serializers.CharField(label=_('名称'), max_length=255)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    organization = serializers.SerializerMethodField(label=_('机构'), method_name='get_organization')

    @staticmethod
    def get_organization(obj):
        org = obj.organization
        if org:
            return {'id': org.id, 'name': org.name, 'name_en': org.name_en}

        return None


class OrgVirtObjCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255, required=True)
    organization_id = serializers.CharField(label=_('机构ID'), required=True)
    remark = serializers.CharField(label=_('备注信息'), max_length=255, allow_blank=True, default='')


class OrgVOContactsPostSerializer(serializers.Serializer):
    contact_ids = serializers.ListField(label=_('联系人ID'), max_length=128, required=True)


class ContactPersonSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(label=_('姓名'), max_length=128, required=True)
    telephone = serializers.CharField(label=_('电话'), max_length=16, required=True)
    email = serializers.EmailField(label=_('邮箱地址'), allow_blank=True, default='')
    address = serializers.CharField(label=_('联系地址'), max_length=255, allow_blank=True, default='')
    remarks = serializers.CharField(max_length=255, label=_('备注'), allow_blank=True, default='')

    creation_time = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    update_time = serializers.DateTimeField(label=_('更新时间'), read_only=True)
