from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class UserQuotaSimpleSerializer(serializers.Serializer):
    id = serializers.CharField()
    tag = serializers.SerializerMethodField(method_name='get_tag')
    expiration_time = serializers.DateTimeField(label=_('过期时间'), default=None)
    deleted = serializers.BooleanField(label=_('删除'), default=False)
    display = serializers.CharField()

    @staticmethod
    def get_tag(obj):
        return {'value': obj.tag, 'display': obj.get_tag_display()}


class ServerBaseSerializer(serializers.Serializer):
    """
    虚拟服务器实例序列化器基类
    """
    id = serializers.CharField()
    name = serializers.CharField()
    vcpus = serializers.IntegerField()
    ram = serializers.IntegerField()
    ipv4 = serializers.CharField()
    public_ip = serializers.BooleanField()
    image = serializers.CharField()
    creation_time = serializers.DateTimeField()
    remarks = serializers.CharField()


class ServerSimpleSerializer(ServerBaseSerializer):
    pass


class ServerSerializer(ServerBaseSerializer):
    """
    虚拟服务器实例序列化器
    """
    endpoint_url = serializers.SerializerMethodField(method_name='get_vms_endpoint_url')
    service = serializers.SerializerMethodField(method_name='get_service')
    user_quota = UserQuotaSimpleSerializer(required=False)
    center_quota = serializers.IntegerField()

    def get_vms_endpoint_url(self, obj):
        service_id_map = self.context.get('service_id_map')
        if service_id_map:
            service = service_id_map.get(obj.service_id)
        else:
            service = obj.service

        if not service:
            return ''

        try:
            return service.data_center.endpoint_vms
        except AttributeError:
            return ''

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
                'service_type': service.service_type_to_str()
            }

        return None


class ServerCreateSerializer(serializers.Serializer):
    """
    创建虚拟服务器序列化器
    """
    service_id = serializers.CharField(label=_('服务'), required=True, help_text=_('服务提供商配置ID'))
    image_id = serializers.CharField(label=_('镜像id'), required=True, help_text=_('系统镜像id'))
    flavor_id = serializers.CharField(label=_('配置样式id'), required=True, help_text=_('硬件配置样式ID'))
    network_id = serializers.CharField(label=_('子网id'), required=False, default='', help_text=_('子网ID'))
    quota_id = serializers.CharField(label=_('资源配额id'), allow_null=True, default=None,
                                     help_text=_('用户资源配额ID'))
    private_quota_id = serializers.CharField(label=_('服务私有资源配额id'), required=False, allow_null=True, default=None,
                                             help_text=_('服务私有资源配额ID'))
    remarks = serializers.CharField(label=_('备注'), required=False, allow_blank=True, max_length=255, default='')

    def validate(self, attrs):
        return attrs


class ServerArchiveSerializer(ServerBaseSerializer):
    """
    虚拟服务器归档记录序列化器
    """
    service = serializers.SerializerMethodField(method_name='get_service')
    user_quota = UserQuotaSimpleSerializer(required=False)
    center_quota = serializers.IntegerField()
    deleted_time = serializers.DateTimeField()

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
                'service_type': service.service_type_to_str()
            }

        return None


class ImageSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    system = serializers.CharField()
    system_type = serializers.CharField()
    creation_time = serializers.DateTimeField()
    desc = serializers.CharField()


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    public = serializers.BooleanField()
    segment = serializers.CharField()


class FlavorSerializer(serializers.Serializer):
    id = serializers.CharField()
    vcpus = serializers.IntegerField(label=_('虚拟CPU数'))
    ram = serializers.IntegerField(label=_('内存MB'))


class UserQuotaSerializer(serializers.Serializer):
    id = serializers.CharField()
    tag = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField(method_name='get_service')
    private_ip_total = serializers.IntegerField(label=_('总私网IP数'), default=0)
    private_ip_used = serializers.IntegerField(label=_('已用私网IP数'), default=0)
    public_ip_total = serializers.IntegerField(label=_('总公网IP数'), default=0)
    public_ip_used = serializers.IntegerField(label=_('已用公网IP数'), default=0)
    vcpu_total = serializers.IntegerField(label=_('总CPU核数'), default=0)
    vcpu_used = serializers.IntegerField(label=_('已用CPU核数'), default=0)
    ram_total = serializers.IntegerField(label=_('总内存大小(MB)'), default=0)
    ram_used = serializers.IntegerField(label=_('已用内存大小(MB)'), default=0)
    disk_size_total = serializers.IntegerField(label=_('总硬盘大小(GB)'), default=0)
    disk_size_used = serializers.IntegerField(label=_('已用硬盘大小(GB)'), default=0)
    expiration_time = serializers.DateTimeField(label=_('过期时间'), default=None)
    deleted = serializers.BooleanField(label=_('删除'), default=False)
    display = serializers.CharField()

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user is None:
            return {'id': None, 'username': None}

        return {'id': user.id, 'username': user.username}

    @staticmethod
    def get_tag(obj):
        return {'value': obj.tag, 'display': obj.get_tag_display()}

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name}

        return {'id': None, 'name': None}


class ServiceQuotaBaseSerializer(serializers.Serializer):
    id = serializers.CharField()
    private_ip_total = serializers.IntegerField(label=_('总私网IP数'), default=0)
    private_ip_used = serializers.IntegerField(label=_('已用私网IP数'), default=0)
    public_ip_total = serializers.IntegerField(label=_('总公网IP数'), default=0)
    public_ip_used = serializers.IntegerField(label=_('已用公网IP数'), default=0)
    vcpu_total = serializers.IntegerField(label=_('总CPU核数'), default=0)
    vcpu_used = serializers.IntegerField(label=_('已用CPU核数'), default=0)
    ram_total = serializers.IntegerField(label=_('总内存大小(MB)'), default=0)
    ram_used = serializers.IntegerField(label=_('已用内存大小(MB)'), default=0)
    disk_size_total = serializers.IntegerField(label=_('总硬盘大小(GB)'), default=0)
    disk_size_used = serializers.IntegerField(label=_('已用硬盘大小(GB)'), default=0)
    creation_time = serializers.DateTimeField(label=_('过期时间'), default=None)
    enable = serializers.BooleanField(label=_('删除'), default=False)
    service = serializers.SerializerMethodField(method_name='get_service')

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name}

        return {'id': None, 'name': None}


class PrivateServiceQuotaSerializer(ServiceQuotaBaseSerializer):
    pass


class ServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    service_type = serializers.SerializerMethodField()
    add_time = serializers.DateTimeField()
    need_vpn = serializers.BooleanField()
    status = serializers.IntegerField()
    data_center = serializers.SerializerMethodField()

    @staticmethod
    def get_data_center(obj):
        c = obj.data_center
        if c is None:
            return {'id': None, 'name': None}

        return {'id': c.id, 'name': c.name}

    @staticmethod
    def get_service_type(obj):
        s = obj.service_type_to_str(obj.service_type)
        if s:
            return s

        return ''


class DataCenterSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    endpoint_vms = serializers.CharField()
    endpoint_object = serializers.CharField()
    endpoint_compute = serializers.CharField()
    endpoint_monitor = serializers.CharField()
    creation_time = serializers.DateTimeField()
    status = serializers.SerializerMethodField(method_name='get_status')
    desc = serializers.CharField()

    @staticmethod
    def get_status(obj):
        s = obj.status
        if s is None:
            return {'code': None, 'message': None}

        return {'code': s, 'message': obj.get_status_display()}
