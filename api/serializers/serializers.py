from django.utils.translation import gettext, gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from service.models import ServiceConfig, ApplyVmService


class DataCenterSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    name_en = serializers.CharField()
    abbreviation = serializers.CharField()
    # endpoint_vms = serializers.CharField()
    # endpoint_object = serializers.CharField()
    # endpoint_compute = serializers.CharField()
    # endpoint_monitor = serializers.CharField()
    creation_time = serializers.DateTimeField()
    status = serializers.SerializerMethodField(method_name='get_status')
    desc = serializers.CharField()
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    sort_weight = serializers.IntegerField()

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


class PaymentHistorySerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    subject = serializers.CharField(label=_('标题'), max_length=256)
    payment_method = serializers.CharField(label=_('付款方式'), max_length=16)
    executor = serializers.CharField(label=_('交易执行人'), help_text=_('记录此次支付交易是谁执行完成的'))
    payer_id = serializers.CharField(label=_('付款人ID'), help_text='user id or vo id')
    payer_name = serializers.CharField(label=_('付款人名称'), help_text='username or vo name')
    payer_type = serializers.CharField(label=_('付款人类型'), max_length=8)
    payable_amounts = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2)
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    coupon_amount = serializers.DecimalField(label=_('券金额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    payment_time = serializers.DateTimeField(label=_('支付时间'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    status = serializers.CharField(label=_('支付状态'), max_length=16)
    status_desc = serializers.CharField(label=_('支付状态描述'), max_length=255)

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
    issuer = serializers.CharField(label=_('发放人'))
    remark = serializers.CharField(label=_('备注'))

    @staticmethod
    def get_app_service(obj):
        if obj.app_service is None:
            return None

        return {
            'id': obj.app_service.id,
            'name': obj.app_service.name,
            'name_en': obj.app_service.name_en,
            'category': obj.app_service.category,
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


class AdminCashCouponSerializer(CashCouponSerializer):
    exchange_code = serializers.SerializerMethodField(label=_('兑换码'), method_name='get_exchange_code')

    @staticmethod
    def get_exchange_code(obj):
        return obj.one_exchange_code


class BaseCashCouponPaymentSerializer(serializers.Serializer):
    """
    券扣费记录序列化器
    """
    cash_coupon_id = serializers.CharField(label=_('资源券编码'))
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    before_payment = serializers.DecimalField(label=_('支付前余额'), max_digits=10, decimal_places=2)
    after_payment = serializers.DecimalField(label=_('支付后余额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class CashCouponPaymentSerializer(BaseCashCouponPaymentSerializer):
    """
    券扣费记录序列化器
    """
    payment_history = PaymentHistorySerializer(allow_null=True)
