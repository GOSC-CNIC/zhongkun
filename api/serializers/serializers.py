from cProfile import label
from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from service.models import ServiceConfig, ApplyVmService


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
    classification = serializers.CharField()
    image_id = serializers.CharField()
    image_desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.SerializerMethodField(method_name='get_default_password')
    pay_type = serializers.CharField()

    @staticmethod
    def get_default_password(obj):
        return obj.raw_default_password


class ServerSimpleSerializer(ServerBaseSerializer):
    pass


class ServerSerializer(ServerBaseSerializer):
    """
    虚拟服务器实例序列化器
    """
    endpoint_url = serializers.SerializerMethodField(method_name='get_vms_endpoint_url')
    service = serializers.SerializerMethodField(method_name='get_service')
    center_quota = serializers.IntegerField()
    vo_id = serializers.CharField()
    user = serializers.SerializerMethodField(method_name='get_user')
    lock = serializers.CharField(label=_('锁'), max_length=16)

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
                'name_en': service.name_en,
                'service_type': service.service_type
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
    remarks = serializers.CharField(label=_('备注'), required=False, allow_blank=True, max_length=255, default='')
    azone_id = serializers.CharField(label=_('可用区'), required=False, allow_null=True, max_length=36, default=None)
    vo_id = serializers.CharField(
        label=_('vo组id'), required=False, allow_null=True, max_length=36, default=None,
        help_text=_('通过vo_id指定为vo组创建云服务器'))
    period = serializers.IntegerField(
        label=_('订购时长（月）'), required=False, allow_null=True, default=None,
        help_text=_('付费模式为预付费时，必须指定订购时长'))

    def validate(self, attrs):
        return attrs


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


class ImageSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    system = serializers.CharField()
    system_type = serializers.CharField()
    creation_time = serializers.DateTimeField()
    desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.CharField()
    min_sys_disk_gb = serializers.IntegerField()
    min_ram_mb = serializers.IntegerField()


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    public = serializers.BooleanField()
    segment = serializers.CharField()


class FlavorSerializer(serializers.Serializer):
    id = serializers.CharField()
    vcpus = serializers.IntegerField(label=_('虚拟CPU数'))
    ram = serializers.IntegerField(label=_('内存MB'))


class ServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    service_type = serializers.CharField()
    cloud_type = serializers.CharField()
    add_time = serializers.DateTimeField()
    need_vpn = serializers.BooleanField()
    status = serializers.CharField()
    data_center = serializers.SerializerMethodField()
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    pay_app_service_id = serializers.CharField(label=_('余额结算APP服务ID'), max_length=36)

    @staticmethod
    def get_data_center(obj):
        c = obj.data_center
        if c is None:
            return {'id': None, 'name': None}

        return {'id': c.id, 'name': c.name}


class DataCenterSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    abbreviation = serializers.CharField()
    endpoint_vms = serializers.CharField()
    endpoint_object = serializers.CharField()
    endpoint_compute = serializers.CharField()
    endpoint_monitor = serializers.CharField()
    creation_time = serializers.DateTimeField()
    status = serializers.SerializerMethodField(method_name='get_status')
    desc = serializers.CharField()
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)

    @staticmethod
    def get_status(obj):
        s = obj.status
        if s is None:
            return {'code': None, 'message': None}

        return {'code': s, 'message': obj.get_status_display()}


class UserSerializer(serializers.Serializer):
    """
    用户
    """
    id = serializers.CharField(label=_('ID'), read_only=True)
    username = serializers.CharField(label=_('用户名'))
    fullname = serializers.SerializerMethodField(method_name='get_fullname')
    role = serializers.JSONField(label=_('角色'))

    @staticmethod
    def get_fullname(obj):
        return obj.get_full_name()


class ApplyOrganizationSerializer(serializers.Serializer):
    """
    机构申请
    """
    id = serializers.CharField(label='id', read_only=True)
    creation_time = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    status = serializers.CharField(label=_('状态'), read_only=True)
    user = serializers.SerializerMethodField(method_name='get_user', read_only=True)
    deleted = serializers.BooleanField(label=_('是否删除'), read_only=True)

    name = serializers.CharField(label=_('机构名称'), max_length=255, required=True)
    name_en = serializers.CharField(label=_('机构英文名称'), max_length=255, required=True, allow_blank=False)
    abbreviation = serializers.CharField(label=_('简称'), max_length=64, required=True)
    independent_legal_person = serializers.BooleanField(label=_('是否独立法人单位'), required=True)
    country = serializers.CharField(label=_('国家/地区'), max_length=128, required=True)
    city = serializers.CharField(label=_('城市'), max_length=128, required=True)
    postal_code = serializers.CharField(
        label=_('邮政编码'), max_length=32, allow_null=True, allow_blank=True, default='')
    address = serializers.CharField(label=_('单位地址'), max_length=256, required=True)
    longitude = serializers.FloatField(label=_('经度'), min_value=-180, max_value=180, allow_null=True, default=0)
    latitude = serializers.FloatField(label=_('纬度'), min_value=-90, max_value=90, allow_null=True, default=0)

    endpoint_vms = serializers.CharField(
        label=_('云主机服务url'), required=False, allow_null=True, allow_blank=True, default=None)
    endpoint_object = serializers.CharField(
        label=_('对象存储服务url'), required=False, allow_null=True, allow_blank=True, default=None)
    endpoint_compute = serializers.CharField(
        label=_('计算服务地址url'), required=False, allow_null=True, allow_blank=True, default=None)
    endpoint_monitor = serializers.CharField(
        label=_('监控服务地址url'), required=False, allow_null=True, allow_blank=True, default=None)
    desc = serializers.CharField(
        label=_('描述'), required=False, max_length=255, allow_null=True, allow_blank=True, default=None)
    logo_url = serializers.CharField(
        label=_('LOGO url'), max_length=256, allow_blank=True, allow_null=True, default='')
    certification_url = serializers.CharField(
        label=_('机构认证代码url'), max_length=256, allow_blank=True, allow_null=True, default='')

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None

    def validate(self, attrs):
        validator = URLValidator(schemes=['http', 'https'])
        attrs = super().validate(attrs)
        endpoint_vms = attrs.get('endpoint_vms', '')
        if endpoint_vms:
            try:
                validator(endpoint_vms)
            except DjangoValidationError as exc:
                raise ValidationError(detail={
                    'endpoint_vms': exc.messages[0] if exc.messages else 'invalid url'
                })

        endpoint_object = attrs.get('endpoint_object', '')
        if endpoint_object:
            try:
                validator(endpoint_object)
            except DjangoValidationError as exc:
                raise ValidationError(detail={
                    'endpoint_object': exc.messages[0] if exc.messages else 'invalid url'
                })

        endpoint_compute = attrs.get('endpoint_compute', '')
        if endpoint_compute:
            try:
                validator(endpoint_compute)
            except DjangoValidationError as exc:
                raise ValidationError(detail={
                    'endpoint_compute': exc.messages[0] if exc.messages else 'invalid url'
                })

        endpoint_monitor = attrs.get('endpoint_monitor', '')
        if endpoint_monitor:
            try:
                validator(endpoint_monitor)
            except DjangoValidationError as exc:
                raise ValidationError(detail={
                    'endpoint_monitor': exc.messages[0] if exc.messages else 'invalid url'
                })

        return attrs


class ApplyVmServiceCreateSerializer(serializers.Serializer):
    """
    服务provider接入申请
    """
    organization_id = serializers.CharField(
        label=_('机构ID'), required=True)
    name = serializers.CharField(label=_('服务名称'), max_length=255, required=True)
    name_en = serializers.CharField(label=_('服务名称'), max_length=255, required=True, allow_blank=False)
    service_type = serializers.CharField(label=_('服务类型'), max_length=32, required=True,
                                         help_text=f'{ApplyVmService.ServiceType.choices}')
    cloud_type = serializers.CharField(label=_('云类型'), max_length=32, required=True,
                                       help_text=f'{ApplyVmService.CLoudType.choices}')
    endpoint_url = serializers.CharField(
        label=_('服务地址url'), max_length=255, required=True,
        validators=[URLValidator(schemes=['http', 'https'])],
        help_text='http(s)://{hostname}:{port}/; type OpenStack is auth url')
    region = serializers.CharField(
        label=_('服务区域/分中心'), max_length=128, default='', allow_blank=True, allow_null=True,
        help_text='region name of OpenSack; center id of EVCloud; not required of VMware')
    api_version = serializers.CharField(
        max_length=32, default='', label=_('API版本'), allow_blank=True, allow_null=True,
        help_text=_('api version of EVCloud and OPenStack; not required of VMware'))
    username = serializers.CharField(
        label=_('用户名'), required=True, help_text=_('用于此服务认证的用户名'))
    password = serializers.CharField(label=_('密码'), required=True, min_length=6, max_length=32)
    project_name = serializers.CharField(
        label='Project Name', required=False, max_length=128, allow_blank=True,
        help_text='only required when OpenStack', default='')
    project_domain_name = serializers.CharField(
        label='Project Domain Name', required=False, max_length=128, allow_blank=True,
        help_text='only required when OpenStack', default='')
    user_domain_name = serializers.CharField(
        label='User Domain Name', required=False, max_length=128, allow_blank=True,
        allow_null=True, default='', help_text='only required when OpenStack')
    remarks = serializers.CharField(
        label=_('备注'), max_length=255, required=False,
        allow_blank=True, allow_null=True, default='')

    need_vpn = serializers.BooleanField(
        label=_('是否需要VPN'), required=True)
    vpn_endpoint_url = serializers.CharField(
        max_length=255, required=False, label=_('VPN服务地址url'), allow_blank=True, default='',
        help_text='http(s)://{hostname}:{port}/; required when "need_vpn" is true; evcloud服务不需要填写')
    vpn_api_version = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default='v3', label=_('VPN API版本'),
        help_text='required when "need_vpn" is true;服务类型是evcloud时，不需要填写')
    vpn_username = serializers.CharField(
        max_length=128, required=False, label=_('用户名'), allow_blank=True, default='',
        help_text=_('required when "need_vpn" is true;用于VPN服务认证的用户名；服务类型是evcloud时，不需要填写'))
    vpn_password = serializers.CharField(
        min_length=6, max_length=32, required=False, label=_('密码'), allow_blank=True, default='',
        help_text='required when "need_vpn" is true;服务类型是evcloud时，不需要填写')

    longitude = serializers.FloatField(
        label=_('经度'), required=False, min_value=-180, max_value=180, allow_null=True, default=0)
    latitude = serializers.FloatField(
        label=_('纬度'), required=False, min_value=-90, max_value=90, allow_null=True, default=0)
    contact_person = serializers.CharField(
        label=_('联系人名称'), max_length=128, required=True)
    contact_email = serializers.EmailField(
        label=_('联系人邮箱'), required=True)
    contact_telephone = serializers.CharField(
        label=_('联系人电话'), max_length=16, required=True)
    contact_fixed_phone = serializers.CharField(
        label=_('联系人固定电话'), max_length=16, allow_blank=True, default='')
    contact_address = serializers.CharField(
        label=_('联系人地址'), max_length=256, required=True)
    logo_url = serializers.CharField(label=_('logo url'), max_length=256,
                                     required=False, default='')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        cloud_type = attrs.get('cloud_type', '')
        if cloud_type not in ServiceConfig.CLoudType.values:
            raise ValidationError(detail={
                'cloud_type': gettext('cloud_type的值无效')})

        service_type = attrs.get('service_type', '')
        if service_type not in ServiceConfig.ServiceType.values:
            raise ValidationError(detail={
                'service_type': gettext('service_type的值无效')})

        region = attrs.get('region', '')
        if service_type in [ServiceConfig.ServiceType.EVCLOUD, ServiceConfig.ServiceType.OPENSTACK]:
            if not region:
                raise ValidationError(detail={
                    'region': gettext('region的值无效')})

        if service_type == ServiceConfig.ServiceType.OPENSTACK:
            project_name = attrs.get('project_name')
            project_domain_name = attrs.get('project_domain_name')
            # user_domain_name = attrs.get('user_domain_name')
            if not project_name:
                raise ValidationError(detail={
                    'project_name': gettext('当服务类型是OpenStack时，"project_name"是必须的')})

            if not project_domain_name:
                raise ValidationError(detail={
                    'project_domain_name': gettext('当服务类型是OpenStack时，"project_domain_name"是必须的')})

            # if not user_domain_name:
            #     raise ValidationError(detail={
            #         'user_domain_name': gettext('当服务类型是OpenStack时，"user_domain_name"是必须的')})

        need_vpn = attrs.get('need_vpn')
        if need_vpn and service_type != ServiceConfig.ServiceType.EVCLOUD:
            vpn_endpoint_url = attrs.get('vpn_endpoint_url')
            vpn_api_version = attrs.get('vpn_api_version')
            vpn_username = attrs.get('vpn_username')
            vpn_password = attrs.get('vpn_password')
            if not vpn_endpoint_url:
                raise ValidationError(detail={
                    'vpn_endpoint_url': gettext('当需要vpn，接入服务类型不是EVCloud时，"vpn_endpoint_url"是必须的')})

            if not vpn_api_version:
                raise ValidationError(detail={
                    'vpn_api_version': gettext('当需要vpn，接入服务类型不是EVCloud时，"vpn_api_version"是必须的')})

            if not vpn_username:
                raise ValidationError(detail={
                    'vpn_username': gettext('当需要vpn，接入服务类型不是EVCloud时，"vpn_username"是必须的')})

            if not vpn_password:
                raise ValidationError(detail={
                    'vpn_password': gettext('当需要vpn，接入服务类型不是EVCloud时，"vpn_password"是必须的')})

        return attrs


class ApplyVmServiceSerializer(serializers.Serializer):
    """
    服务provider接入申请
    """
    id = serializers.CharField()
    user = serializers.SerializerMethodField(method_name='get_user')
    creation_time = serializers.DateTimeField()
    approve_time = serializers.DateTimeField()
    status = serializers.CharField()

    organization_id = serializers.CharField()
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    region = serializers.CharField()
    service_type = serializers.CharField()
    cloud_type = serializers.CharField()
    endpoint_url = serializers.CharField()
    api_version = serializers.CharField()
    username = serializers.CharField()
    password = serializers.SerializerMethodField(method_name='get_password')
    project_name = serializers.CharField()
    project_domain_name = serializers.CharField()
    user_domain_name = serializers.CharField()

    need_vpn = serializers.BooleanField()
    vpn_endpoint_url = serializers.CharField()
    vpn_api_version = serializers.CharField()
    vpn_username = serializers.CharField()
    vpn_password = serializers.SerializerMethodField(method_name='get_vpn_password')
    # service = serializers
    deleted = serializers.BooleanField()

    contact_person = serializers.CharField()
    contact_email = serializers.EmailField()
    contact_telephone = serializers.CharField()
    contact_fixed_phone = serializers.CharField()
    contact_address = serializers.CharField()
    remarks = serializers.CharField()
    logo_url = serializers.CharField()

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return None

    @staticmethod
    def get_password(obj):
        return obj.raw_password()

    @staticmethod
    def get_vpn_password(obj):
        return obj.raw_vpn_password()


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
        label=_('总内存大小(MB)'), min_value=0, required=False, allow_null=True, default=None,
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
    ram_used = serializers.IntegerField(label=_('已用内存大小(MB)'), read_only=True)
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


class VoSerializer(serializers.Serializer):
    id = serializers.CharField(
        label=_('组ID'), read_only=True)
    name = serializers.CharField(label=_('组名称'), max_length=255, required=True)
    company = serializers.CharField(label=_('单位'), max_length=256, required=True)
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
    usernames = serializers.ListField(label=_('用户名'), max_length=1000, required=True, allow_null=False, allow_empty=False)


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


class MonitorJobCephSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('监控的CEPH集群名称'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控的CEPH集群英文名称'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('CEPH集群标签名称'), max_length=255, default='')
    service_id = serializers.CharField(label=_('服务'))
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorJobServerSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('监控的主机集群'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控的主机集群英文名'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('主机集群的标签名称'), max_length=255, default='')
    service_id = serializers.CharField(label=_('服务'))
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorJobVideoMeetingSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('科技云会服务节点院所名称'), max_length=255, default='')
    name_en = serializers.CharField(label=_('科技云会服务节点院所英名称'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('视频会议节点的标签名称'), max_length=255, default='')
    creation = serializers.DateTimeField(label=_('创建时间'))
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))


class AvailabilityZoneSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('可用区ID'))
    name = serializers.CharField(label=_('可用区名称'))


class OrderSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('订单编号'))
    order_type = serializers.CharField(label=_('订单类型'))
    status = serializers.CharField(label=_('订单状态'), max_length=16)
    total_amount = serializers.DecimalField(label=_('总金额'), max_digits=10, decimal_places=2, default=0.0)
    pay_amount = serializers.DecimalField(label=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)
    payable_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2)
    balance_amount = serializers.DecimalField(label=_('余额支付金额'), max_digits=10, decimal_places=2)
    coupon_amount = serializers.DecimalField(label=_('券支付金额'), max_digits=10, decimal_places=2)

    service_id = serializers.CharField(label=_('服务id'), max_length=36)
    service_name = serializers.CharField(label=_('服务名称'), max_length=255)
    resource_type = serializers.CharField(label=_('资源类型'), max_length=16)
    instance_config = serializers.JSONField(label=_('资源的规格和配置'))
    period = serializers.IntegerField(label=_('订购时长(月)'))

    payment_time = serializers.DateTimeField(label=_('支付时间'))
    pay_type = serializers.CharField(label=_('付费方式'), max_length=16)

    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=64)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('VO组名'), max_length=256)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    cancelled_time = serializers.DateTimeField(label=_('作废时间'))
    app_service_id = serializers.CharField(label=_('app服务id'), max_length=36)


class ResourceSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    order_id = serializers.CharField(label=_('订单编号'))
    resource_type = serializers.CharField(label=_('订单编号'))
    instance_id = serializers.CharField(label=_('资源实例id'), max_length=36)
    instance_status = serializers.CharField(label=_('资源创建结果'))
    delivered_time = serializers.DateTimeField(label=_('资源交付时间'))


class OrderDetailSerializer(OrderSerializer):
    resources = ResourceSerializer(many=True)


class MeteringServerSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('订单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    trade_amount = serializers.DecimalField(label=_('交易金额'), max_digits=10, decimal_places=2)
    daily_statement_id = serializers.CharField(label=_('日结算单ID'))
    service_id = serializers.CharField(label=_('服务'))
    server_id = serializers.CharField(label=_('云服务器ID'), max_length=36)
    date = serializers.DateField(label=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('vo组名'), max_length=255)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    cpu_hours = serializers.FloatField(label=_('CPU Hour'), help_text=_('云服务器的CPU Hour数'))
    ram_hours = serializers.FloatField(label=_('内存GiB Hour'), help_text=_('云服务器的内存Gib Hour数'))
    disk_hours = serializers.FloatField(label=_('系统盘GiB Hour'), help_text=_('云服务器的系统盘Gib Hour数'))
    public_ip_hours = serializers.FloatField(label=_('IP Hour'), help_text=_('云服务器的公网IP Hour数'))
    snapshot_hours = serializers.FloatField(label=_('快照GiB Hour'), help_text=_('云服务器的快照小时数'))
    upstream = serializers.FloatField(label=_('上行流量GiB'), help_text=_('云服务器的上行流量Gib'))
    downstream = serializers.FloatField(label=_('下行流量GiB'), help_text=_('云服务器的下行流量Gib'))
    pay_type = serializers.CharField(label=_('云服务器付费方式'), max_length=16)


class PaymentHistorySerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    subject = serializers.CharField(label=_('标题'), max_length=256)
    payment_method = serializers.CharField(label=_('付款方式'), max_length=16)
    executor = serializers.CharField(label=_('交易执行人'), help_text=_('记录此次支付交易是谁执行完成的'))
    payer_id = serializers.CharField(label=_('付款人ID'), help_text='user id or vo id')
    payer_name = serializers.CharField(label=_('付款人名称'), help_text='username or vo name')
    payer_type = serializers.CharField(label=_('付款人类型'), max_length=8)
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    coupon_amount = serializers.DecimalField(label=_('券金额'), max_digits=10, decimal_places=2)
    payment_time = serializers.DateTimeField(label=_('支付时间'))
    type = serializers.CharField(label=_('支付类型'), max_length=16)
    remark = serializers.CharField(label=_('备注信息'), max_length=255)

    order_id = serializers.CharField(label=_('订单ID'), max_length=36)
    app_id = serializers.CharField(label=_('应用ID'), max_length=36)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36)


class BasePointAccountSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    balance = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class VoPointAccountSerializer(BasePointAccountSerializer):
    vo = serializers.SerializerMethodField(method_name='get_vo')

    @staticmethod
    def get_vo(obj):
        return {'id': obj.vo_id}


class UserPointAccountSerializer(BasePointAccountSerializer):
    user = serializers.SerializerMethodField(method_name='get_user')

    @staticmethod
    def get_user(obj):
        return {'id': obj.user_id}


class CashCouponSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    effective_time = serializers.DateTimeField(label=_('生效时间'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'))
    balance = serializers.DecimalField(label=_('余额'), max_digits=10, decimal_places=2)
    status = serializers.CharField(label=_('状态'), max_length=16)
    granted_time = serializers.DateTimeField(label=_('领取/发放时间'))
    owner_type = serializers.CharField(label=_('所属类型'), max_length=16)
    app_service = serializers.SerializerMethodField(label=_('适用服务'))
    user = serializers.SerializerMethodField(label=_('用户'))
    vo = serializers.SerializerMethodField(label=_('VO组'))
    activity = serializers.SerializerMethodField(label=_('活动'))

    @staticmethod
    def get_app_service(obj):
        if obj.app_service is None:
            return None

        return {
            'id': obj.app_service.id,
            'name': obj.app_service.name,
            'name_en': obj.app_service.name_en,
            'service_id': obj.app_service.service_id
        }

    @staticmethod
    def get_user(obj):
        if obj.user is None:
            return None

        return {'id': obj.user.id, 'username': obj.user.username}

    @staticmethod
    def get_vo(obj):
        if obj.vo is None:
            return None

        return {'id': obj.vo.id, 'name': obj.vo.name}

    @staticmethod
    def get_activity(obj):
        if obj.activity is None:
            return None

        return {'id': obj.activity.id, 'name': obj.activity.name}


class BaseCashCouponPaymentSerializer(serializers.Serializer):
    """
    券扣费记录序列化器
    """
    cash_coupon_id = serializers.CharField(label=_('代金券编码'))
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    before_payment = serializers.DecimalField(label=_('支付前余额'), max_digits=10, decimal_places=2)
    after_payment = serializers.DecimalField(label=_('支付后余额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class CashCouponPaymentSerializer(BaseCashCouponPaymentSerializer):
    """
    券扣费记录序列化器
    """
    payment_history = PaymentHistorySerializer(allow_null=True)


class DailyStatementServerSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('日结算单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2, default=0.0)
    payable_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2, default=0.0)
    trade_amount = serializers.DecimalField(label=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)
    payment_status = serializers.CharField(label=_('支付状态'), max_length=16)
    payment_history_id = serializers.CharField(label=_('支付记录ID'), max_length=36)
    service_id = serializers.CharField(label=_('服务id'), max_length=36)
    date = serializers.DateField(label=_('日结算单日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=64)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('VO组名'), max_length=256)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)


class DailyStatementServerDetailSerializer(DailyStatementServerSerializer):
    service = serializers.SerializerMethodField(method_name='get_service')

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
