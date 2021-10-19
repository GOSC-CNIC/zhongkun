from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from service.models import ServiceConfig
from activity.models import QuotaActivity


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
    classification = serializers.CharField()
    image_id = serializers.CharField()
    image_desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.SerializerMethodField(method_name='get_default_password')

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
    user_quota = UserQuotaSimpleSerializer(required=False)
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
    service_id = serializers.CharField(label=_('服务'), required=True, help_text=_('服务提供商配置ID'))
    image_id = serializers.CharField(label=_('镜像id'), required=True, help_text=_('系统镜像id'))
    flavor_id = serializers.CharField(label=_('配置样式id'), required=True, help_text=_('硬件配置样式ID'))
    network_id = serializers.CharField(label=_('子网id'), required=False, default='', help_text=_('子网ID'))
    quota_id = serializers.CharField(label=_('资源配额id'), required=True,
                                     help_text=_('用户个人或vo组的资源配额ID'))
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
    vo_id = serializers.CharField()

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
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
    classification = serializers.CharField(
        label=_('资源配额归属类型'), read_only=True, help_text=_('标识配额属于申请者个人的，还是vo组的'))
    vo_id = serializers.CharField(label=_('vo组ID'), read_only=True)

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


class ServiceSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    service_type = serializers.CharField()
    add_time = serializers.DateTimeField()
    need_vpn = serializers.BooleanField()
    status = serializers.CharField()
    data_center = serializers.SerializerMethodField()

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
    vo_id = serializers.CharField(label=_('VO组ID'), write_only=True, required=False,
                                  allow_null=True, allow_blank=False,
                                  help_text=_('指示为指定的VO组配额申请；不提交此内容时属于个人资源配额申请'))
    service_id = serializers.CharField(label=_('服务ID'), write_only=True, max_length=36, required=True)
    private_ip = serializers.IntegerField(label=_('总私网IP数'), required=False,
                                          allow_null=True, min_value=0, default=0)
    public_ip = serializers.IntegerField(label=_('总公网IP数'), required=False,
                                         allow_null=True, min_value=0, default=0)
    vcpu = serializers.IntegerField(label=_('总CPU核数'), required=False,
                                    allow_null=True, min_value=0, default=0)
    ram = serializers.IntegerField(label=_('总内存大小(MB)'), required=False,
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
    deleted = serializers.BooleanField(label=_('删除'), read_only=True)
    classification = serializers.CharField(
        label=_('资源配额归属类型'), read_only=True, help_text=_('标识配额属于申请者个人的，还是vo组的'))
    result_desc = serializers.CharField(label=_('审批结果描述'), max_length=255, read_only=True)

    @staticmethod
    def get_service(obj):
        s = obj.service
        if s:
            return {'id': s.id, 'name': s.name}

        return None


class ApplyQuotaRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(label=_('拒绝原因'), max_length=255, required=True, allow_blank=False)


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
            return {'id': s.id, 'name': s.username}

        return None

    @staticmethod
    def get_approve_user(obj):
        s = obj.approve_user
        if s:
            return {'id': s.id, 'name': s.username}

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
    ram = serializers.IntegerField(label=_('总内存大小(MB)'), required=False,
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
    service_type = serializers.CharField(label=_('服务类型'), required=True)
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
        label=_('经度'), required=False, allow_null=True, default=0)
    latitude = serializers.FloatField(
        label=_('纬度'), required=False, allow_null=True, default=0)
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
            return {'id': obj.service.id, 'name': obj.service.name}

        return {'id': None, 'name': None}


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


class ApplyQuotaDetailWithVoSerializer(ApplyQuotaDetailSerializer):
    vo = VoSerializer(required=False)


class UserQuotaDetailSerializer(UserQuotaSerializer):
    vo = VoSerializer(required=False)


class QuotaActivitySerializer(serializers.Serializer):
    """
    配额活动序列化器
    """
    id = serializers.CharField(label=_('id'), max_length=36, read_only=True)
    got_count = serializers.IntegerField(label=_('已领取数量'), default=0, read_only=True)
    service = serializers.SerializerMethodField(method_name='get_service', read_only=True)
    user = serializers.SerializerMethodField(method_name='get_user', read_only=True)
    creation_time = serializers.DateTimeField(label=_('活动创建时间'), read_only=True)
    service_id = serializers.CharField(label=_('服务id'), max_length=36, write_only=True, required=True,
                                       help_text=_('接入的云主机服务provider id'))

    name = serializers.CharField(label=_('配额活动名称'), max_length=255, required=True)
    name_en = serializers.CharField(label=_('配额活动英文名称'), max_length=255, required=True)
    start_time = serializers.DateTimeField(label=_('活动开始时间'), required=True)
    end_time = serializers.DateTimeField(label=_('活动结束时间'), required=True)
    count = serializers.IntegerField(label=_('总数量'), min_value=1, required=True)
    times_per_user = serializers.IntegerField(label=_('每人可领取次数'), min_value=1, required=True,
                                              help_text=_('每个用户可领取次数'))
    status = serializers.CharField(label=_('活动状态'), max_length=16, required=True,
                                   help_text=_('可选值') + f'{QuotaActivity.Status.values}')

    tag = serializers.CharField(label=_('配额类型'), max_length=32, required=True,
                                help_text=_('可选值') + f'{QuotaActivity.Tag.values}')
    cpus = serializers.IntegerField(label=_('虚拟cpu数量'), min_value=1, max_value=1000, required=True)
    private_ip = serializers.IntegerField(label=_('私网IP数'), min_value=0, required=True)
    public_ip = serializers.IntegerField(label=_('公网IP数'), min_value=0, required=True)
    ram = serializers.IntegerField(label=_('内存大小(MB)'), min_value=1024, required=True)
    disk_size = serializers.IntegerField(label=_('总硬盘大小(GB)'), min_value=0, required=True)
    expiration_time = serializers.DateTimeField(label=_('配额过期时间'), required=True,
                                                help_text=_('过期后不能再用于创建资源'))
    duration_days = serializers.IntegerField(label=_('资源使用时长'), min_value=1, required=True,
                                             help_text=_('使用此配额创建的资源的有效使用时长'))

    def validate(self, attrs):
        status = attrs.get('status')
        tag = attrs.get('tag')
        if status not in QuotaActivity.Status.values:
            raise ValidationError(detail={
                'status': gettext('status的值无效')
            })

        if tag not in QuotaActivity.Tag.values:
            raise ValidationError(detail={
                'tag': gettext('tag的值无效')
            })

        private_ip = attrs.get('private_ip')
        public_ip = attrs.get('public_ip')
        disk_size = attrs.get('disk_size')
        if private_ip == 0 and public_ip == 0 and disk_size == 0:
            raise ValidationError(detail={
                'private_ip': gettext('private_ip、public_ip和disk_size不能都为0，否则配额没有使用意义')
            })

        return attrs

    @staticmethod
    def get_user(obj):
        if obj.user:
            return {'id': obj.user.id, 'username': obj.user.username}

        return None

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

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