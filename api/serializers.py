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
    expiration_time = serializers.DateTimeField()
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
    quota_id = serializers.CharField(label=_('资源配额id'), required=True,
                                     help_text=_('用户资源配额ID'))
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
    duration_days = serializers.IntegerField(label=_('资源可用时长'))

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


class ApplyQuotaCreateSerializer(serializers.Serializer):
    """
    用户资源配额申请
    """
    service_id = serializers.CharField(label=_('服务ID'), write_only=True, max_length=36, required=True)
    private_ip = serializers.IntegerField(label=_('总私网IP数'), required=False,
                                          allow_null=True, min_value=0, default=0)
    public_ip = serializers.IntegerField(label=_('总公网IP数'), required=False,
                                         allow_null=True, min_value=0, default=0)
    vcpu = serializers.IntegerField(label=_('总CPU核数'), required=False,
                                    allow_null=True, min_value=0, default=0)
    ram = serializers.IntegerField(label=_('总内存大小(GB)'), required=False,
                                   allow_null=True, min_value=0, default=0)
    disk_size = serializers.IntegerField(label=_('总硬盘大小(GB)'), required=False,
                                         allow_null=True, min_value=0, default=0)
    duration_days = serializers.IntegerField(label=_('申请使用时长(天)'), required=True, min_value=1)
    company = serializers.CharField(label=_('申请人单位'), required=False, max_length=64,
                                    allow_null=True, allow_blank=True, default=None)
    contact = serializers.CharField(label=_('联系方式'), required=False, max_length=64,
                                    allow_null=True, allow_blank=True, default=None)
    purpose = serializers.CharField(label=_('用途'), required=False, max_length=255,
                                    allow_null=True, allow_blank=True, default=None)


class ApplyQuotaSerializer(ApplyQuotaCreateSerializer):
    id = serializers.CharField(label='ID', read_only=True)
    creation_time = serializers.DateTimeField(label=_('申请时间'), read_only=True)
    status = serializers.CharField(label=_('状态'), read_only=True)
    service = serializers.SerializerMethodField(label=_('服务'), read_only=True,
                                                method_name='get_service')

    @staticmethod
    def get_service(obj):
        s = obj.service
        if s:
            return {'id': s.id, 'name': s.name}

        return None


class ApplyQuotaDetailSerializer(ApplyQuotaSerializer):
    user = serializers.SerializerMethodField(label=_('申请用户'), read_only=True,
                                             method_name='get_user')
    approve_user = serializers.SerializerMethodField(label=_('审批人'), read_only=True,
                                                     method_name='get_approve_user')
    approve_time = serializers.DateTimeField(label=_('审批时间'), read_only=True)

    @staticmethod
    def get_user(obj):
        s = obj.user
        if s:
            return {'id': s.id, 'name': s.name}

        return None

    @staticmethod
    def get_approve_user(obj):
        s = obj.approve_user
        if s:
            return {'id': s.id, 'name': s.name}

        return None


class ApplyQuotaPatchSerializer(serializers.Serializer):
    """
    用户资源配额申请修改
    """
    service_id = serializers.CharField(label=_('服务ID'), write_only=True, max_length=36, required=False,
                                       allow_null=True, default=None)
    private_ip = serializers.IntegerField(label=_('总私网IP数'), required=False,
                                          allow_null=True, min_value=0, default=None)
    public_ip = serializers.IntegerField(label=_('总公网IP数'), required=False,
                                         allow_null=True, min_value=0, default=None)
    vcpu = serializers.IntegerField(label=_('总CPU核数'), required=False,
                                    allow_null=True, min_value=0, default=None)
    ram = serializers.IntegerField(label=_('总内存大小(GB)'), required=False,
                                   allow_null=True, min_value=0, default=None)
    disk_size = serializers.IntegerField(label=_('总硬盘大小(GB)'), required=False,
                                         allow_null=True, min_value=0, default=None)
    duration_days = serializers.IntegerField(label=_('申请使用时长(天)'), required=False,
                                             allow_null=True, min_value=1, default=None)
    company = serializers.CharField(label=_('申请人单位'), required=False, max_length=64,
                                    allow_null=True, allow_blank=True, default=None)
    contact = serializers.CharField(label=_('联系方式'), required=False, max_length=64,
                                    allow_null=True, allow_blank=True, default=None)
    purpose = serializers.CharField(label=_('用途'), required=False, max_length=255,
                                    allow_null=True, allow_blank=True, default=None)


