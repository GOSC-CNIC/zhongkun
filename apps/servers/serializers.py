from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from utils.model import PayType
from apps.app_wallet.trade_serializers import CashCouponSerializer
from apps.order.serializers import OrderSerializer


class PeriodSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    period = serializers.IntegerField(label=_('月数'))
    enable = serializers.BooleanField(label='启用')
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    service_id = serializers.CharField(label=_('服务单元ID'), max_length=36, required=True)


class FlavorSerializer(serializers.Serializer):
    id = serializers.CharField()
    flavor_id = serializers.CharField(label=_('服务端规格ID'))
    vcpus = serializers.IntegerField(label=_('虚拟CPU数'))
    ram = serializers.IntegerField(label=_('内存GiB'))
    disk = serializers.IntegerField(label=_('硬盘GB'))
    service_id = serializers.CharField(label=_('服务单元id'))
    enable = serializers.BooleanField(label='启用')
    ram_gib = serializers.SerializerMethodField(method_name='get_ram_gib', label=_('内存GiB'))

    @staticmethod
    def get_ram_gib(obj):
        return obj.ram


class FlavorCreateSerializer(serializers.Serializer):
    service_id = serializers.CharField(label=_('服务单元id'), required=True)
    vcpus = serializers.IntegerField(label=_('CPU数'), required=True)
    ram = serializers.IntegerField(label=_('内存GiB'), required=True)
    enable = serializers.BooleanField(label=_('是否启用'), required=True)


class ImageSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    release = serializers.CharField()
    version = serializers.CharField()
    architecture = serializers.CharField()
    system_type = serializers.CharField()
    creation_time = serializers.DateTimeField()
    desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.CharField()
    min_sys_disk_gb = serializers.IntegerField()
    min_ram_mb = serializers.IntegerField()


class ImageOldSerializer(ImageSerializer):
    system = serializers.SerializerMethodField(method_name='get_system')

    @staticmethod
    def get_system(obj):
        return obj.release


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    public = serializers.BooleanField()
    segment = serializers.CharField()


class AvailabilityZoneSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('可用区ID'))
    name = serializers.CharField(label=_('可用区名称'))
    available = serializers.BooleanField(label=_('是否可用'))


class ServerBaseSerializer(serializers.Serializer):
    """
    虚拟服务器实例序列化器基类
    """
    id = serializers.CharField()
    name = serializers.CharField()
    vcpus = serializers.IntegerField()
    ram = serializers.SerializerMethodField(method_name='get_ram')
    ram_gib = serializers.IntegerField()
    ipv4 = serializers.CharField()
    public_ip = serializers.BooleanField()
    image = serializers.CharField()
    creation_time = serializers.DateTimeField()
    expiration_time = serializers.DateTimeField()
    remarks = serializers.CharField()
    classification = serializers.CharField()
    image_id = serializers.CharField()
    image_desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.SerializerMethodField(method_name='get_default_password')
    pay_type = serializers.CharField()
    img_sys_type = serializers.CharField(max_length=32, label=_('镜像系统类型'))
    img_sys_arch = serializers.CharField(max_length=32, label=_('镜像系统架构'))
    img_release = serializers.CharField(max_length=32, label=_('镜像系统发行版'))
    img_release_version = serializers.CharField(max_length=32, label=_('镜像系统发行版版本'))
    instance_id = serializers.CharField(max_length=128, label=_('云主机实例ID'), help_text=_('各接入服务中云主机的ID'))
    created_user = serializers.CharField(label=_('创建人'), max_length=128)

    @staticmethod
    def get_default_password(obj):
        return obj.raw_default_password

    @staticmethod
    def get_ram(obj):
        return obj.ram_gib


class ServerSimpleSerializer(ServerBaseSerializer):
    pass


class ServerSerializer(ServerBaseSerializer):
    """
    虚拟服务器实例序列化器
    """
    service = serializers.SerializerMethodField(method_name='get_service')
    center_quota = serializers.IntegerField()
    vo_id = serializers.CharField()
    vo = serializers.SerializerMethodField(method_name='get_vo')
    user = serializers.SerializerMethodField(method_name='get_user')
    lock = serializers.CharField(label=_('锁'), max_length=16)

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
                'name_en': service.name_en,
                'service_type': service.service_type,
                'endpoint_url': service.endpoint_url
            }

        return None

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {
                'id': user.id,
                'username': user.username
            }

        return None

    @staticmethod
    def get_vo(obj):
        vo = obj.vo
        if vo:
            return {
                'id': vo.id,
                'name': vo.name
            }

        return None


class ServerCreateSerializer(serializers.Serializer):
    """
    创建虚拟服务器序列化器
    """
    pay_type = serializers.CharField(label=_('付费模式'), required=True, max_length=16)
    service_id = serializers.CharField(label=_('服务'), required=True, help_text=_('服务提供商配置ID'))
    image_id = serializers.CharField(label=_('镜像id'), required=True, help_text=_('系统镜像id'))
    flavor_id = serializers.CharField(label=_('配置样式id'), required=True, help_text=_('硬件配置样式ID'))
    network_id = serializers.CharField(label=_('子网id'), required=True, help_text=_('子网ID'))
    systemdisk_size = serializers.IntegerField(
        label=_('系统盘大小（GiB）'), min_value=50, max_value=500, required=False, allow_null=True,
        help_text=_('指定云服务期的系统盘大小，单位GiB，只允许50的倍数值，50、100、150等'), default=None)
    remarks = serializers.CharField(label=_('云主机备注'), required=False, allow_blank=True, max_length=255, default='')
    azone_id = serializers.CharField(label=_('可用区'), required=False, allow_null=True, max_length=36, default=None)
    period = serializers.IntegerField(
        label=_('订购时长，单位由period_unit指定'), required=False, allow_null=True, default=None,
        help_text=_('付费模式为预付费时，必须指定订购时长'))
    period_unit = serializers.CharField(
        label=_('时长单位，默认（月）'), required=False, allow_null=True, default=None,
        help_text=_('和时长'))
    number = serializers.IntegerField(label=_('订购资源数量'), required=False, allow_null=True, default=1)
    vo_id = serializers.CharField(
        label=_('vo组id'), required=False, allow_null=True, max_length=36, default=None,
        help_text=_('通过vo_id指定为vo组创建云服务器，不能和“username”一起提交'))
    username = serializers.CharField(
        label=_('用户名'), required=False, allow_null=True, max_length=36, default=None,
        help_text=_('通过“username”指定为用户创建订购云主机，不能和“vo_id”一起提交，管理员参数'))

    def validate(self, attrs):
        return attrs


class ServerCreateTaskSerializer(ServerCreateSerializer):
    """
    管理员云主机订购任务序列化器
    """
    pay_type = serializers.CharField(
        label=_('付费模式'), required=True, max_length=16, help_text=f'只允许预付费模式，{PayType.PREPAID.value}')
    task_desc = serializers.CharField(
        label=_('任务描述'), required=False, allow_blank=True, max_length=255, default='',
    help_text=_('管理员提交此云主机订购任务的描述信息'))


class ServerArchiveSerializer(ServerBaseSerializer):
    """
    虚拟服务器归档记录序列化器
    """
    server_id = serializers.CharField()
    service = serializers.SerializerMethodField(method_name='get_service')
    center_quota = serializers.IntegerField()
    deleted_time = serializers.DateTimeField()
    vo_id = serializers.CharField()

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
                'name_en': service.name_en,
                'service_type': service.service_type
            }

        return None


class ServerRebuildSerializer(serializers.Serializer):
    """
    创建虚拟服务器序列化器
    """
    image_id = serializers.CharField(label=_('镜像id'), required=True, help_text=_('系统镜像id'))


class VmServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    service_type = serializers.CharField()
    cloud_type = serializers.CharField()
    add_time = serializers.DateTimeField()
    need_vpn = serializers.BooleanField()
    status = serializers.CharField()
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    pay_app_service_id = serializers.CharField(label=_('余额结算APP服务ID'), max_length=36)
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    disk_available = serializers.BooleanField(label=_('提供云硬盘服务'))

    @staticmethod
    def get_org_data_center(obj):
        odc = obj.org_data_center
        if odc is None:
            return None

        data = {
            'id': odc.id, 'name': odc.name, 'name_en': odc.name_en, 'sort_weight': odc.sort_weight
        }
        org = odc.organization
        if org is None:
            data['organization'] = None
        else:
            data['organization'] = {
                'id': org.id, 'name': org.name, 'name_en': org.name_en
            }

        return data


class AdminServiceSerializer(VmServiceSerializer):
    region_id = serializers.CharField(max_length=128, label=_('服务区域/分中心ID'))
    endpoint_url = serializers.CharField(
        max_length=255, label=_('服务地址url'), help_text='http(s)://{hostname}:{port}/')
    api_version = serializers.CharField(
        max_length=64, label=_('API版本'), help_text=_('预留，主要EVCloud使用'))
    username = serializers.CharField(max_length=128, label=_('用户名'), help_text=_('用于此服务认证的用户名'))
    extra = serializers.CharField(max_length=1024, label=_('其他配置'), help_text=_('json格式'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))


class VmServiceBaseQuotaUpdateSerializer(serializers.Serializer):
    private_ip_total = serializers.IntegerField(
        label=_('总私网IP数'), min_value=0, required=False, allow_null=True, default=None,
        help_text=_('不更改不要提交此内容'))
    public_ip_total = serializers.IntegerField(
        label=_('总公网IP数'), min_value=0, required=False, allow_null=True, default=None,
        help_text=_('不更改不要提交此内容'))
    vcpu_total = serializers.IntegerField(
        label=_('总CPU核数'), min_value=0, required=False, allow_null=True, default=None,
        help_text=_('不更改不要提交此内容'))
    ram_total = serializers.IntegerField(
        label=_('总内存大小(GB)'), min_value=0, required=False, allow_null=True, default=None,
        help_text=_('不更改不要提交此内容'))
    disk_size_total = serializers.IntegerField(
        label=_('总硬盘大小(GB)'), min_value=0, required=False, allow_null=True, default=None,
        help_text=_('不更改不要提交此内容'))


class VmServicePrivateQuotaUpdateSerializer(VmServiceBaseQuotaUpdateSerializer):
    pass


class VmServiceShareQuotaUpdateSerializer(VmServiceBaseQuotaUpdateSerializer):
    pass


class VmServiceBaseQuotaSerializer(VmServiceBaseQuotaUpdateSerializer):
    private_ip_used = serializers.IntegerField(label=_('已用私网IP数'), read_only=True)
    public_ip_used = serializers.IntegerField(label=_('已用公网IP数'), read_only=True)
    vcpu_used = serializers.IntegerField(label=_('已用CPU核数'), read_only=True)
    ram_used = serializers.IntegerField(label=_('已用内存大小(GiB)'), read_only=True)
    disk_size_used = serializers.IntegerField(label=_('已用硬盘大小(GB)'), read_only=True)
    creation_time = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    enable = serializers.BooleanField(label=_('有效状态'), read_only=True,
                                      help_text=_('选中，资源配额生效；未选中，无法申请分中心资源'))
    service = serializers.SerializerMethodField(method_name='get_service')

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

        return {'id': None, 'name': None, 'name_en': None}


class VmServicePrivateQuotaSerializer(VmServiceBaseQuotaSerializer):
    pass


class VmServiceShareQuotaSerializer(VmServiceBaseQuotaSerializer):
    pass


class ServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    service_type = serializers.CharField()
    cloud_type = serializers.CharField()
    endpoint_url = serializers.CharField()
    add_time = serializers.DateTimeField()
    need_vpn = serializers.BooleanField()
    status = serializers.CharField()
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    pay_app_service_id = serializers.CharField(label=_('余额结算APP服务ID'), max_length=36)
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    disk_available = serializers.BooleanField(label=_('提供云硬盘服务'))
    only_admin_visible = serializers.BooleanField(label=_('仅管理员可见'))
    version = serializers.CharField(max_length=32, label=_('版本号'))
    version_update_time = serializers.DateTimeField()

    @staticmethod
    def get_org_data_center(obj):
        odc = obj.org_data_center
        if odc is None:
            return None

        data = {
            'id': odc.id, 'name': odc.name, 'name_en': odc.name_en, 'sort_weight': odc.sort_weight
        }
        org = odc.organization
        if org is None:
            data['organization'] = None
        else:
            data['organization'] = {
                'id': org.id, 'name': org.name, 'name_en': org.name_en, 'sort_weight': org.sort_weight
            }

        return data


class ServiceAdminSerializer(ServiceSerializer):
    admin_users = serializers.SerializerMethodField(label=_('服务单元管理员'), method_name='get_admin_users')

    @staticmethod
    def get_admin_users(obj):
        return obj.admin_users


class ServerSnapshotSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID')
    name = serializers.CharField(max_length=128, label=_('快照名称'))
    size = serializers.IntegerField(label=_('容量大小GiB'))
    remarks = serializers.CharField(max_length=255, label=_('备注'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'))
    pay_type = serializers.CharField(label=_('计费方式'), max_length=16)
    classification = serializers.CharField(label=_('快照归属类型'), max_length=16)
    user = serializers.SerializerMethodField(label=_('创建者'), method_name='get_user')
    vo = serializers.SerializerMethodField(label=_('项目组'), method_name='get_vo')
    server = serializers.SerializerMethodField(label=_('归属云主机'), method_name='get_server')
    service = serializers.SerializerMethodField(label=_('服务单元'), method_name='get_service')
    system_name = serializers.CharField(max_length=255)
    system_release = serializers.CharField(max_length=64)

    @staticmethod
    def get_user(obj):
        if obj.user:
            return {'id': obj.user.id, 'username': obj.user.username}

        return None

    @staticmethod
    def get_vo(obj):
        if not obj.vo_id or not obj.vo:
            return None

        return {'id': obj.vo.id, 'name': obj.vo.name}

    @staticmethod
    def get_server(obj):
        server = obj.get_server()
        if not server:
            return None

        return {
            'id': server.id,
            'vcpus': server.vcpus, 'ram_gib': server.ram_gib,
            'ipv4': server.ipv4, 'image': server.image,
            'creation_time': serializers.DateTimeField().to_representation(server.creation_time),
            'expiration_time': serializers.DateTimeField().to_representation(server.expiration_time),
            'remarks': server.remarks
        }

    @staticmethod
    def get_service(obj):
        if not obj.service_id or not obj.service:
            return None

        return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}


class SnapshotCreateSerializer(serializers.Serializer):
    snapshot_name = serializers.CharField(label=_('快照名称'), required=True, max_length=128)
    server_id = serializers.CharField(label=_('云主机ID'), required=True)
    period = serializers.IntegerField(label=_('订购时长，单位由period_unit指定'), required=True)
    period_unit = serializers.CharField(label=_('时长单位'), required=True, help_text='choice in [day、month]')
    description = serializers.CharField(label=_('快照描述'), required=False, allow_blank=True, max_length=255, default='')


class SnapshotRenewSerializer(serializers.Serializer):
    snapshot_id = serializers.CharField(label=_('快照ID'), required=True, max_length=36)
    period = serializers.IntegerField(label=_('订购时长，单位由period_unit指定'), required=True)
    period_unit = serializers.CharField(label=_('时长单位'), required=True, help_text='choice in [day、month]')


class SnapshotUpdateSerializer(serializers.Serializer):
    snapshot_name = serializers.CharField(
        label=_('快照名称'), required=False, allow_blank=True, max_length=128, default=None)
    description = serializers.CharField(
        label=_('快照描述'), required=False, allow_blank=True, max_length=255, default=None)


class AdminResTaskSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    status = serializers.CharField(label=_('状态'), max_length=16)
    status_desc = serializers.CharField(label=_('状态描述'), max_length=255)
    progress = serializers.CharField(label=_('任务进度'), max_length=16)
    submitter_id = serializers.CharField(label=_('提交人id'), max_length=36)
    submitter = serializers.CharField(label=_('提交人'), max_length=128)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    task_desc = serializers.CharField(max_length=255, label=_('任务描述'))
    service = serializers.SerializerMethodField(label=_('服务单元'), method_name='get_service')
    order = serializers.SerializerMethodField(label=_('订单编号'), method_name='get_order')
    coupon_id = serializers.CharField(label=_('资源券编号'))

    @staticmethod
    def get_service(obj):
        if not obj.service:
            return None

        return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

    @staticmethod
    def get_order(obj):
        od = obj.order
        if not od:
            return None

        return {
            'id': od.id, 'resource_type': od.resource_type, 'number': od.number,
            'order_type': od.order_type,
            'total_amount': serializers.DecimalField(max_digits=10, decimal_places=2).to_representation(od.total_amount)
        }


class AdminResTaskDetailSerializer(AdminResTaskSerializer):
    coupon = CashCouponSerializer(label=_('资源券'), allow_null=True)
    order = OrderSerializer(label=_('订单'), allow_null=True)
