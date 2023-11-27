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


class OrgVirtObjCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255, required=True)
    organization_id = serializers.CharField(label=_('机构ID'), required=True)
    remark = serializers.CharField(label=_('备注信息'), max_length=255, allow_blank=True, default='')


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


class IPv4RangeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255, allow_blank=True, default='')
    start_address = serializers.CharField(label=_('起始地址'), required=True)
    end_address = serializers.CharField(label=_('截止地址'), required=True)
    mask_len = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=0, max_value=32)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=65535)
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255, allow_blank=True, default='')


class IPv4RangeSplitSerializer(serializers.Serializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    fake = serializers.BooleanField(
        label=_('假拆分'), allow_null=True, default=False,
        help_text=_('true(假装拆分，询问拆分规划)；其他值或不提交此参数（正常真实拆分地址段）'))


class IPv4RangeMergeSerializer(serializers.Serializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    ip_range_ids = serializers.ListField(
        label=_('ip地址段id列表'), child=serializers.CharField(label='ip地址段id', max_length=36),
        min_length=1, max_length=256, required=True)
    fake = serializers.BooleanField(
        label=_('假合并'), allow_null=True, default=False,
        help_text=_('true(假装合并，询问合并结果)；其他值或不提交此参数（正常真实合并地址段）'))


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
