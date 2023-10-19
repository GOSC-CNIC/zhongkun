from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


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


class IPv4RangeSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    name = serializers.CharField(label=_('名称'), max_length=255, required=True)
    status = serializers.CharField(label=_('状态'), max_length=16)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    assigned_time = serializers.DateTimeField(label=_('分配时间'))
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255)
    remark = serializers.CharField(label=_('机构管理员备注信息'), max_length=255)
    start_address = serializers.IntegerField(label=_('起始地址'))
    end_address = serializers.IntegerField(label=_('截止地址'))
    mask_len = serializers.IntegerField(label=_('子网掩码长度'))
    asn = serializers.SerializerMethodField(label=_('AS编号'), method_name='get_asn')
    org_virt_obj = OrgVirtualObjectSimpleSerializer(label=_('机构虚拟对象'))

    @staticmethod
    def get_asn(obj):
        asn = obj.asn
        if asn:
            return {'id': asn.id, 'number': asn.number}

        return None


class IPAMUserRoleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    is_admin = serializers.BooleanField(
        label=_('科技网IP管理员'), default=False, help_text=_('选中，用户拥有科技网IP管理功能的管理员权限'))
    is_readonly = serializers.BooleanField(
        label=_('IP管理全局只读权限'), default=False, help_text=_('选中，用户拥有科技网IP管理功能的全局只读权限'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user = serializers.SerializerMethodField(label=_('用户'), method_name='get_user')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None
