from adapters.evcloud.adapter import EVCloudAdapter
from adapters.exceptions import UnsupportedServiceType, MethodNotSupportInService
from service.models import ServiceConfig


SERVICE_TYPE_EVCLOUD = 'evcloud'
SERVICE_TYPE_OPENSTACK = 'openstack'


def get_service_client(service, **kwargs):
    style = SERVICE_TYPE_EVCLOUD
    if service.service_type == service.SERVICE_OPENSTACK:
        style = SERVICE_TYPE_OPENSTACK

    return OneServiceClient(style=style, endpoint_url=service.endpoint_url, api_version=service.api_version,
                            auth=kwargs.get('auth'))


def get_service_vpn_client(service: ServiceConfig, **kwargs):
    if service.service_type == service.SERVICE_EVCLOUD:
        endpoint_url = service.endpoint_url
    else:
        endpoint_url = service.vpn_endpoint_url

    return VPNClient(endpoint_url=endpoint_url, api_version=service.vpn_api_version, auth=kwargs.get('auth'))


def get_adapter_class(style: str = 'evcloud'):
    """
    获取适配器

    :param style: in ['evcloud', 'openstack']
    :return:
        subclass of base.AdapterBase

    :raises: UnsupportedServiceType
    """
    if style.lower() == SERVICE_TYPE_EVCLOUD:
        return EVCloudAdapter

    raise UnsupportedServiceType()


class OneServiceClient:
    def __init__(self, style, endpoint_url, api_version, auth=None):
        """
        :param style: style in ['evcloud', 'openstack']
        :param endpoint_url:
        :param api_version:
        """
        adapter_class = get_adapter_class(style)
        self.adapter = adapter_class(endpoint_url=endpoint_url, api_version=api_version, auth=auth)

    def __getattr__(self, attr):
        try:
            return getattr(self.adapter, attr)
        except AttributeError:
            raise MethodNotSupportInService()

    def authenticate(self, *args, **kwargs):
        return self.adapter.authenticate(*args, **kwargs)

    def server_create(self, *args, **kwargs):
        return self.adapter.server_create(*args, **kwargs)

    def server_delete(self, *args, **kwargs):
        return self.adapter.server_delete(*args, **kwargs)

    def server_action(self, *args, **kwargs):
        return self.adapter.server_action(*args, **kwargs)

    def server_status(self, *args, **kwargs):
        return self.adapter.server_status(*args, **kwargs)

    def server_vnc(self, *args, **kwargs):
        return self.adapter.server_vnc(*args, **kwargs)

    def list_images(self, *args, **kwargs):
        return self.adapter.list_images(*args, **kwargs)

    def list_networks(self, *args, **kwargs):
        return self.adapter.list_networks(*args, **kwargs)

    def list_flavors(self, *args, **kwargs):
        return self.adapter.list_flavors(*args, **kwargs)

    def get_flavor(self, *args, **kwargs):
        return self.adapter.get_flavor(*args, **kwargs)

    def get_network(self, *args, **kwargs):
        return self.adapter.get_network(*args, **kwargs)


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
