from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


class BaseIPAMSerializer(serializers.Serializer):
    class Meta:
        ref_name = 'ipam'   # 在线文档 drf-yasg 需要区分同名的 Serializer


class OrgVirtualObjectSimpleSerializer(BaseIPAMSerializer):
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


class OrgVirtObjCreateSerializer(BaseIPAMSerializer):
    name = serializers.CharField(label=_('名称'), max_length=255, required=True)
    organization_id = serializers.CharField(label=_('机构ID'), required=True)
    remark = serializers.CharField(label=_('备注信息'), max_length=255, allow_blank=True, default='')


class OrgVOContactsPostSerializer(BaseIPAMSerializer):
    contact_ids = serializers.ListField(label=_('联系人ID'), max_length=128, required=True)


class IPv4RangeSerializer(BaseIPAMSerializer):
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


class IPv4RangeCreateSerializer(BaseIPAMSerializer):
    name = serializers.CharField(label=_('名称'), max_length=255, allow_blank=True, default='')
    start_address = serializers.CharField(label=_('起始地址'), required=True, max_length=16)
    end_address = serializers.CharField(label=_('截止地址'), required=True, max_length=16)
    mask_len = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=0, max_value=32)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=65535)
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255, allow_blank=True, default='')


class IPv4RangeSplitSerializer(BaseIPAMSerializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    fake = serializers.BooleanField(
        label=_('假拆分'), allow_null=True, default=False,
        help_text=_('true(假装拆分，询问拆分规划)；其他值或不提交此参数（正常真实拆分地址段）'))


class SubIPv4Range(BaseIPAMSerializer):
    start_address = serializers.IntegerField(label=_('起始地址'), min_value=0, required=True)
    end_address = serializers.IntegerField(label=_('截止地址'), min_value=0, required=True)
    prefix = serializers.IntegerField(label=_('前缀（子网掩码）长度'), required=True, min_value=0, max_value=32)


class IPv4RangePlanSplitSerializer(BaseIPAMSerializer):
    sub_ranges = serializers.ListField(child=SubIPv4Range(), label=_('拆分计划子网段'), required=True)


class IPv4RangeMergeSerializer(BaseIPAMSerializer):
    new_prefix = serializers.IntegerField(label=_('子网掩码长度'), required=True, min_value=1, max_value=31)
    ip_range_ids = serializers.ListField(
        label=_('ip地址段id列表'), child=serializers.CharField(label='ip地址段id', max_length=36),
        min_length=1, max_length=256, required=True)
    fake = serializers.BooleanField(
        label=_('假合并'), allow_null=True, default=False,
        help_text=_('true(假装合并，询问合并结果)；其他值或不提交此参数（正常真实合并地址段）'))


class IPAMUserRoleSerializer(BaseIPAMSerializer):
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


class IPv4RangeRecordSerializer(BaseIPAMSerializer):
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


class IPv4AddressSerializer(BaseIPAMSerializer):
    id = serializers.CharField(label='ID', read_only=True)
    ip_address = serializers.IntegerField(label=_('IP地址'))
    remark = serializers.CharField(label=_('机构管理员备注信息'), max_length=255)
    # creation_time = serializers.DateTimeField(label=_('创建时间'))
    # update_time = serializers.DateTimeField(label=_('更新时间'))


class IPv4AddressAdminSerializer(IPv4AddressSerializer):
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255)


class IPv6RangeSerializer(BaseIPAMSerializer):
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


class IPv6RangeCreateSerializer(BaseIPAMSerializer):
    name = serializers.CharField(label=_('名称'), max_length=255, allow_blank=True, default='')
    start_address = serializers.CharField(
        label=_('起始地址'), required=True, max_length=40, help_text='2400:dd01:1010:30::')
    end_address = serializers.CharField(
        label=_('截止地址'), required=True, max_length=40, help_text='2400:dd01:1010:30:ffff:ffff:ffff:ffff')
    prefixlen = serializers.IntegerField(label=_('子网前缀'), required=True, min_value=0, max_value=128)
    asn = serializers.IntegerField(label=_('AS编号'), required=True, min_value=0, max_value=65535)
    admin_remark = serializers.CharField(label=_('科技网管理员备注信息'), max_length=255, allow_blank=True, default='')


class ContactPersonSerializer(BaseIPAMSerializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(label=_('姓名'), max_length=128, required=True)
    telephone = serializers.CharField(label=_('电话'), max_length=16, required=True)
    email = serializers.EmailField(label=_('邮箱地址'), allow_blank=True, default='')
    address = serializers.CharField(label=_('联系地址'), max_length=255, allow_blank=True, default='')
    remarks = serializers.CharField(max_length=255, label=_('备注'), allow_blank=True, default='')

    creation_time = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    update_time = serializers.DateTimeField(label=_('更新时间'), read_only=True)
