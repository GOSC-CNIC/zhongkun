from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.app_net_manage.serializers import OrgVirtualObjectSimpleSerializer


class NetIPamUserRoleSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    is_ipam_admin = serializers.BooleanField(
        label=_('IP管理员'), default=False, help_text=_('选中，用户拥有网络IP管理功能的管理员权限'))
    is_ipam_readonly = serializers.BooleanField(
        label=_('IP管理全局只读权限'), default=False, help_text=_('选中，用户拥有网络IP管理功能的全局只读权限'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user = serializers.SerializerMethodField(label=_('用户'), method_name='get_user')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

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


class IPv4RangeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255, allow_blank=True, default='')
    start_address = serializers.CharField(label=_('起始地址'), required=True, max_length=16)
    end_address = serializers.CharField(label=_('截止地址'), required=True, max_length=16)
    mask_len = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=0, max_value=32)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=4294967295)
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255, allow_blank=True, default='')


class IPv4RangeSplitSerializer(serializers.Serializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    fake = serializers.BooleanField(
        label=_('假拆分'), allow_null=True, default=False,
        help_text=_('true(假装拆分，询问拆分规划)；其他值或不提交此参数（正常真实拆分地址段）'))


class SubIPv4Range(serializers.Serializer):
    start_address = serializers.IntegerField(label=_('起始地址'), min_value=0, required=True)
    end_address = serializers.IntegerField(label=_('截止地址'), min_value=0, required=True)
    prefix = serializers.IntegerField(label=_('前缀（子网掩码）长度'), required=True, min_value=0, max_value=32)


class IPv4RangePlanSplitSerializer(serializers.Serializer):
    sub_ranges = serializers.ListField(child=SubIPv4Range(), label=_('拆分计划子网段'), required=True)


class IPv4RangeMergeSerializer(serializers.Serializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    ip_range_ids = serializers.ListField(
        label=_('ip地址段id列表'), child=serializers.CharField(label='ip地址段id', max_length=36),
        min_length=1, max_length=256, required=True)
    fake = serializers.BooleanField(
        label=_('假合并'), allow_null=True, default=False,
        help_text=_('true(假装合并，询问合并结果)；其他值或不提交此参数（正常真实合并地址段）'))


class IPv4RangeRecordSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    record_type = serializers.CharField(label=_('记录类型'), max_length=16)
    start_address = serializers.IntegerField(label=_('起始地址'))
    end_address = serializers.IntegerField(label=_('截止地址'))
    mask_len = serializers.IntegerField(label=_('子网掩码长度'))
    ip_ranges = serializers.JSONField(label=_('拆分或合并的IP段'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    user = serializers.SerializerMethodField(label=_('操作用户'), method_name='get_user')
    org_virt_obj = OrgVirtualObjectSimpleSerializer(label=_('机构二级对象'))

    @staticmethod
    def get_user(obj):
        if obj.user is None:
            return None

        return {'id': obj.user.id, 'username': obj.user.username}


class IPv4AddressSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    ip_address = serializers.IntegerField(label=_('IP地址'))
    remark = serializers.CharField(label=_('机构管理员备注信息'), max_length=255)
    # creation_time = serializers.DateTimeField(label=_('创建时间'))
    # update_time = serializers.DateTimeField(label=_('更新时间'))


class IPv4AddressAdminSerializer(IPv4AddressSerializer):
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255)


class IPv6RangeSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    name = serializers.CharField(label=_('名称'), max_length=255, required=True)
    status = serializers.CharField(label=_('状态'), max_length=16)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    assigned_time = serializers.DateTimeField(label=_('分配时间'))
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255)
    remark = serializers.CharField(label=_('机构管理员备注信息'), max_length=255)
    start_address = serializers.SerializerMethodField(label=_('起始地址'), method_name='get_start_address')
    end_address = serializers.SerializerMethodField(label=_('截止地址'), method_name='get_end_address')
    prefixlen = serializers.IntegerField(label=_('前缀长度'))
    asn = serializers.SerializerMethodField(label=_('AS编号'), method_name='get_asn')
    org_virt_obj = OrgVirtualObjectSimpleSerializer(label=_('机构虚拟对象'))

    @staticmethod
    def get_asn(obj):
        asn = obj.asn
        if asn:
            return {'id': asn.id, 'number': asn.number}

        return None

    @staticmethod
    def get_start_address(obj):
        try:
            return str(obj.start_address_obj)
        except Exception as exc:
            return ''

    @staticmethod
    def get_end_address(obj):
        try:
            return str(obj.end_address_obj)
        except Exception as exc:
            return ''


class IPv6RangeCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255, allow_blank=True, default='')
    start_address = serializers.CharField(
        label=_('起始地址'), required=True, max_length=40, help_text='2400:dd01:1010:30::')
    end_address = serializers.CharField(
        label=_('截止地址'), required=True, max_length=40, help_text='2400:dd01:1010:30:ffff:ffff:ffff:ffff')
    prefixlen = serializers.IntegerField(label=_('子网前缀'), required=True, min_value=0, max_value=128)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=4294967295)
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255, allow_blank=True, default='')


class IPv6RangeRecordSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', read_only=True)
    creation_time = serializers.DateTimeField(label='创建时间')
    record_type = serializers.CharField(label='记录类型', max_length=16)
    start_address = serializers.SerializerMethodField(label=_('起始地址'), method_name='get_start_address')
    end_address = serializers.SerializerMethodField(label=_('截止地址'), method_name='get_end_address')
    prefixlen = serializers.IntegerField(label=_('前缀长度'))
    ip_ranges = serializers.JSONField(label='拆分或合并的IP段')
    remark = serializers.CharField(label='备注信息', max_length=255)
    user = serializers.SerializerMethodField(label='操作用户', method_name='get_user')
    org_virt_obj = OrgVirtualObjectSimpleSerializer(label='机构二级对象')

    @staticmethod
    def get_user(obj):
        if obj.user is None:
            return None

        return {'id': obj.user.id, 'username': obj.user.username}

    @staticmethod
    def get_start_address(obj):
        try:
            return str(obj.start_address_obj)
        except Exception as exc:
            return ''

    @staticmethod
    def get_end_address(obj):
        try:
            return str(obj.end_address_obj)
        except Exception as exc:
            return ''


class SubIPv6Range(serializers.Serializer):
    start_address = serializers.CharField(label=_('起始地址'), max_length=40, required=True)
    end_address = serializers.CharField(label=_('截止地址'), max_length=40, required=True)
    prefix = serializers.IntegerField(label=_('前缀（子网掩码）长度'), required=True, min_value=0, max_value=128)


class IPv6RangePlanSplitSerializer(serializers.Serializer):
    sub_ranges = serializers.ListField(child=SubIPv6Range(), label=_('拆分计划子网段'), required=True, max_length=256)


class SubIPv6RangeSerializer(serializers.Serializer):
    start = serializers.CharField(label=_('起始地址'), max_length=40, required=True)
    end = serializers.CharField(label=_('截止地址'), max_length=40, required=True)
    prefix = serializers.IntegerField(label=_('前缀（子网掩码）长度'), required=True, min_value=0, max_value=128)


class IPv6RangeSpiltPlanPost(SubIPv6RangeSerializer):
    new_prefix = serializers.IntegerField(
        label=_('拆分前缀长度'), required=True, min_value=0, max_value=128, write_only=True)


class IPv6RangeMergeSerializer(serializers.Serializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=127)
    ip_range_ids = serializers.ListField(
        label=_('ip地址段id列表'), child=serializers.CharField(label='ip地址段id', max_length=36),
        min_length=1, max_length=256, required=True)
    fake = serializers.BooleanField(
        label=_('假合并'), allow_null=True, default=False,
        help_text=_('true(假装合并，询问合并结果)；其他值或不提交此参数（正常真实合并地址段）'))


class IPv4SupernetCreateSerializer(serializers.Serializer):
    start_address = serializers.IntegerField(label=_('起始地址'), required=True, min_value=0, max_value=4294967295)
    end_address = serializers.IntegerField(label=_('截止地址'), required=True, min_value=0, max_value=4294967295)
    mask_len = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=0, max_value=32)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=4294967295)
    remark = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, default='')


class IPv4SupernetSerializer(IPv4SupernetCreateSerializer):
    id = serializers.CharField()
    name = serializers.CharField()
    status = serializers.CharField()
    creation_time = serializers.DateTimeField()
    update_time = serializers.DateTimeField()
    operator = serializers.CharField()
    used_ip_count = serializers.IntegerField()
    total_ip_count = serializers.IntegerField()


class ExternalIPv4RangeSerializer(serializers.Serializer):
    start_address = serializers.IntegerField(label=_('起始地址'), required=True, min_value=0, max_value=4294967295)
    end_address = serializers.IntegerField(label=_('截止地址'), required=True, min_value=0, max_value=4294967295)
    mask_len = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=0, max_value=32)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=4294967295)
    org_name = serializers.CharField(label=_('机构'), max_length=128, allow_blank=True, default='')
    country = serializers.CharField(label=_('国家'), max_length=64, allow_blank=True, default='')
    city = serializers.CharField(label=_('城市'), max_length=128, allow_blank=True, default='')
    remark = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, default='')

    id = serializers.CharField(label='id', read_only=True)
    name = serializers.CharField(label='名称', read_only=True)
    operator = serializers.CharField(label='操作人', read_only=True)
    creation_time = serializers.DateTimeField(label='创建时间', read_only=True)
    update_time = serializers.DateTimeField(label='更新时间', read_only=True)
