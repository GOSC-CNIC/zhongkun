from service.models import ServiceConfig

from .evcloud.adapter import EVCloudAdapter
from .openstack.adapter import OpenStackAdapter
from .vmware.adapter import VmwareAdapter
from .uniscloud.adapter import UnisAdapter
from .exceptions import UnsupportedServiceType, MethodNotSupportInService
from .params import ParamsName


SERVICE_TYPE_EVCLOUD = 'evcloud'
SERVICE_TYPE_OPENSTACK = 'openstack'
SERVICE_TYPE_VMWARE = 'vmware'
SERVICE_TYPE_UNIS_CLOUD = 'unis-cloud'


def get_service_client(service: ServiceConfig, **kwargs):
    service_type = service.service_type
    if service_type == service.ServiceType.EVCLOUD:
        style = SERVICE_TYPE_EVCLOUD
    elif service_type == service.ServiceType.OPENSTACK:
        style = SERVICE_TYPE_OPENSTACK
    elif service_type == service.ServiceType.VMWARE:
        style = SERVICE_TYPE_VMWARE
    # elif service_type == service.ServiceType.UNIS_CLOUD:
    #     style = SERVICE_TYPE_UNIS_CLOUD
    else:
        raise UnsupportedServiceType(extend_msg=service_type)

    params = service.extra_params()
    if service.region_id:
        params[ParamsName.REGION] = service.region_id

    auth = kwargs.pop('auth') if 'auth' in kwargs else None
    params.update(kwargs)
    return OneServiceClient(style=style, endpoint_url=service.endpoint_url, api_version=service.api_version,
                            auth=auth, **params)


def get_service_vpn_client(service: ServiceConfig, **kwargs):
    if service.service_type == service.ServiceType.EVCLOUD:
        endpoint_url = service.endpoint_url
    else:
        endpoint_url = service.vpn_endpoint_url

    return VPNClient(endpoint_url=endpoint_url, api_version=service.vpn_api_version, auth=kwargs.get('auth'))


def get_adapter_class(style: str = 'evcloud'):
    """
    获取适配器

    :param style: in ['evcloud', 'openstack', 'vmware']
    :return:
        subclass of base.AdapterBase

    :raises: UnsupportedServiceType
    """
    map_adapters = {
        SERVICE_TYPE_EVCLOUD: EVCloudAdapter,
        SERVICE_TYPE_OPENSTACK: OpenStackAdapter,
        SERVICE_TYPE_VMWARE: VmwareAdapter,
        SERVICE_TYPE_UNIS_CLOUD: UnisAdapter,
    }
    style = style.lower()

    if style in map_adapters:
        return map_adapters[style]

    raise UnsupportedServiceType()


def adapter_method_not_support(action=""):
    def _decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except NotImplementedError as e:
                raise MethodNotSupportInService(message=f'adapter not support this action "{action}"')

        return wrapper
    return _decorator


class OneServiceClient:
    def __init__(self, style, endpoint_url, api_version, auth=None, **kwargs):
        """
        :param style: style in ['evcloud', 'openstack']
        :param endpoint_url:
        :param api_version:
        """
        adapter_class = get_adapter_class(style)
        self.adapter = adapter_class(endpoint_url=endpoint_url, api_version=api_version, auth=auth, **kwargs)

    def __getattr__(self, attr):
        try:
            return getattr(self.adapter, attr)
        except AttributeError:
            raise MethodNotSupportInService()

    @adapter_method_not_support(action='authenticate')
    def authenticate(self, *args, **kwargs):
        return self.adapter.authenticate(*args, **kwargs)

    @adapter_method_not_support(action='create server')
    def server_create(self, *args, **kwargs):
        return self.adapter.server_create(*args, **kwargs)

    @adapter_method_not_support(action='delete server')
    def server_delete(self, *args, **kwargs):
        return self.adapter.server_delete(*args, **kwargs)

    @adapter_method_not_support(action='action server')
    def server_action(self, *args, **kwargs):
        return self.adapter.server_action(*args, **kwargs)

    @adapter_method_not_support(action='get server status')
    def server_status(self, *args, **kwargs):
        return self.adapter.server_status(*args, **kwargs)

    @adapter_method_not_support(action='get server vnc')
    def server_vnc(self, *args, **kwargs):
        return self.adapter.server_vnc(*args, **kwargs)

    @adapter_method_not_support(action='rebuild server')
    def server_rebuild(self, params, **kwargs):
        return self.adapter.server_rebuild(params=params, **kwargs)

    @adapter_method_not_support(action='get server detail')
    def server_detail(self, *args, **kwargs):
        return self.adapter.server_detail(*args, **kwargs)

    @adapter_method_not_support(action='list images')
    def list_images(self, *args, **kwargs):
        return self.adapter.list_images(*args, **kwargs)

    @adapter_method_not_support(action='list networks')
    def list_networks(self, *args, **kwargs):
        return self.adapter.list_networks(*args, **kwargs)

    @adapter_method_not_support(action='get network detail')
    def network_detail(self, *args, **kwargs):
        return self.adapter.network_detail(*args, **kwargs)


class VPNClient:
    def __init__(self, endpoint_url, api_version='v3', auth=None):
        """
        :param endpoint_url: vpn service url
        :param api_version:
        """
        adapter_class = get_adapter_class(style='evcloud')
        self.adapter = adapter_class(endpoint_url=endpoint_url, api_version=api_version, auth=auth)

    def __getattr__(self, attr):
        try:
            return getattr(self.adapter, attr)
        except AttributeError:
            raise MethodNotSupportInService()

    def authenticate(self, *args, **kwargs):
        return self.adapter.authenticate(*args, **kwargs)

    def get_vpn(self, *args, **kwargs):
        return self.adapter.get_vpn(*args, **kwargs)

    def create_vpn(self, *args, **kwargs):
        return self.adapter.create_vpn(*args, **kwargs)

    def get_vpn_or_create(self, *args, **kwargs):
        return self.adapter.get_vpn_or_create(*args, **kwargs)

    def vpn_change_password(self, *args, **kwargs):
        return self.adapter.vpn_change_password(*args, **kwargs)

    def get_vpn_config_file_url(self, *args, **kwargs):
        return self.adapter.get_vpn_config_file_url()

    def get_vpn_ca_file_url(self, *args, **kwargs):
        return self.adapter.get_vpn_ca_file_url()
