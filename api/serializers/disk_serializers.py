from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from servers.models import Server


class DiskCreateSerializer(serializers.Serializer):
    """
    创建云硬盘序列化器
    """
    pay_type = serializers.CharField(label=_('付费模式'), required=True, max_length=16)
    service_id = serializers.CharField(label=_('服务单元'), required=True, help_text=_('服务提供商配置ID'))
    azone_id = serializers.CharField(label=_('可用区'), required=True, max_length=36)
    size = serializers.IntegerField(label=_('云盘大小（GiB）'), min_value=1, max_value=10240, required=True)
    period = serializers.IntegerField(
        label=_('订购时长（月）'), required=False, allow_null=True, default=None,
        help_text=_('付费模式为预付费时，必须指定订购时长'))
    remarks = serializers.CharField(label=_('备注'), required=False, allow_blank=True, max_length=255, default='')
    vo_id = serializers.CharField(
        label=_('vo组id'), required=False, allow_null=True, max_length=36, default=None,
        help_text=_('通过vo_id指定为vo组创建云服务器'))


class DiskSerializer(serializers.Serializer):
    """
    云硬盘序列化器
    """
    id = serializers.CharField(max_length=36, label='ID')
    name = serializers.CharField(max_length=255, label=_('云硬盘名称'))
    size = serializers.IntegerField(label=_('容量大小GiB'))
    service = serializers.SerializerMethodField(label=_('服务单元'), method_name='get_service')
    azone_id = serializers.CharField(label=_('可用区Id'), max_length=36)
    azone_name = serializers.CharField(label=_('可用区名称'), max_length=36)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))
    task_status = serializers.CharField(label=_('创建状态'), max_length=16)
    expiration_time = serializers.DateTimeField(label=_('过期时间'))
    pay_type = serializers.CharField(label=_('计费方式'), max_length=16)
    classification = serializers.CharField(label=_('云硬盘归属类型'), help_text=_('标识云硬盘属于申请者个人的，还是vo组的'))
    user = serializers.SerializerMethodField(label=_('创建者'), method_name='get_user')
    vo = serializers.SerializerMethodField(label=_('项目组'), method_name='get_vo')
    lock = serializers.CharField(label=_('锁'), max_length=16, help_text=_('加锁锁定云硬盘，防止误操作'))
    deleted = serializers.BooleanField(label=_('删除状态'), help_text=_('选中表示已删除'))
    server = serializers.SerializerMethodField(label=_('挂载于云主机'), method_name='get_server')
    mountpoint = serializers.CharField(label=_('挂载点/设备名'), help_text='例如 "/dev/vdc"')
    attached_time = serializers.DateTimeField(label=_('最后一次挂载时间'))
    detached_time = serializers.DateTimeField(label=_('最后一次卸载时间'))

    @staticmethod
    def get_service(obj):
        sv = obj.service
        if sv:
            return {'id': sv.id, 'name': sv.name, 'name_en': sv.name_en}

        return None

    @staticmethod
    def get_user(obj):
        u = obj.user
        if u:
            return {'id': u.id, 'username': u.username}

        return None

    @staticmethod
    def get_vo(obj):
        v = obj.vo
        if v:
            return {'id': v.id, 'name': v.name}

        return None

    @staticmethod
    def get_server(obj):
        s: Server = obj.server
        if s:
            return {'id': s.id, 'ipv4': s.ipv4, 'vcpus': s.vcpus, 'ram': s.ram_gib, 'image': s.image}

        return None


class ServerDiskSerializer(serializers.Serializer):
    """
    云硬盘序列化器
    """
    id = serializers.CharField(max_length=36, label='ID')
    size = serializers.IntegerField(label=_('容量大小GiB'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'))
    pay_type = serializers.CharField(label=_('计费方式'), max_length=16)
    mountpoint = serializers.CharField(label=_('挂载点/设备名'), help_text='例如 "/dev/vdc"')
    attached_time = serializers.DateTimeField(label=_('最后一次挂载时间'))
    detached_time = serializers.DateTimeField(label=_('最后一次卸载时间'))
