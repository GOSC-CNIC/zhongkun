from apps.servers.models import ServiceConfig

from .evcloud.adapter import EVCloudAdapter
from .openstack.adapter import OpenStackAdapter
from .vmware.adapter import VmwareAdapter
from .uniscloud.adapter import UnisAdapter
from .aliyun.adapter import AliyunAdapter
from .exceptions import UnsupportedServiceType, MethodNotSupportInService
from .params import BaseAdapterParams, GenericAdapterParams, OpenStackParams
from . import inputs, outputs


class AdapterType:
    EVCLOUD = 'evcloud'
    OPENSTACK = 'openstack'
    VMWARE = 'vmware'
    UNIS_CLOUD = 'unis-cloud'
    ALIYUN = 'aliyun'


def get_adapter_params(adapter_type: str):
    ap_cls = GenericAdapterParams
    if adapter_type == AdapterType.OPENSTACK:
        ap_cls = OpenStackParams

    return ap_cls().get_custom_params()


def get_adapter_params_for_service(service: ServiceConfig) -> dict:
    style = get_service_style(service)
    return get_adapter_params(adapter_type=style)


def get_service_style(service: ServiceConfig):
    service_type = service.service_type
    if service_type == service.ServiceType.EVCLOUD:
        style = AdapterType.EVCLOUD
    elif service_type == service.ServiceType.OPENSTACK:
        style = AdapterType.OPENSTACK
    elif service_type == service.ServiceType.VMWARE:
        style = AdapterType.VMWARE
    elif service_type == service.ServiceType.ALIYUN:
        style = AdapterType.ALIYUN
    # elif service_type == service.ServiceType.UNIS_CLOUD:
    #     style = AdapterType.UNIS_CLOUD
    else:
        raise UnsupportedServiceType(extend_msg=service_type)

    return style


def get_service_client(service: ServiceConfig, **kwargs):
    style = get_service_style(service)
    params = service.extra_params()
    if service.region_id:
        params[BaseAdapterParams.REGION] = service.region_id

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
        AdapterType.EVCLOUD: EVCloudAdapter,
        AdapterType.OPENSTACK: OpenStackAdapter,
        AdapterType.VMWARE: VmwareAdapter,
        AdapterType.UNIS_CLOUD: UnisAdapter,
        AdapterType.ALIYUN: AliyunAdapter,
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

    @adapter_method_not_support(action='list availability zones')
    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput) -> outputs.ListAvailabilityZoneOutput:
        return self.adapter.list_availability_zones(params=params)

    @adapter_method_not_support(action='create disk')
    def disk_create(self, params: inputs.DiskCreateInput) -> outputs.DiskCreateOutput:
        return self.adapter.disk_create(params=params)

    @adapter_method_not_support(action='pretend create disk')
    def disk_create_pretend(self, params: inputs.DiskCreateInput) -> outputs.DiskCreatePretendOutput:
        return self.adapter.disk_create_pretend(params=params)

    @adapter_method_not_support(action='delete disk')
    def disk_delete(self, params: inputs.DiskDeleteInput) -> outputs.DiskDeleteOutput:
        return self.adapter.disk_delete(params=params)

    @adapter_method_not_support(action='attach disk')
    def disk_attach(self, params: inputs.DiskAttachInput) -> outputs.DiskAttachOutput:
        return self.adapter.disk_attach(params=params)

    @adapter_method_not_support(action='detach disk')
    def disk_detach(self, params: inputs.DiskDetachInput) -> outputs.DiskDetachOutput:
        return self.adapter.disk_detach(params=params)

    @adapter_method_not_support(action='get disk detail')
    def disk_detail(self, params: inputs.DiskDetailInput) -> outputs.DiskDetailOutput:
        return self.adapter.disk_detail(params=params)

    @adapter_method_not_support(action='get quota')
    def get_quota(self, params: inputs.QuotaInput) -> outputs.QuotaOutput:
        return self.adapter.get_quota(params=params)

    @adapter_method_not_support(action='get version')
    def get_version(self) -> outputs.VersionOutput:
        return self.adapter.get_version()

    @adapter_method_not_support(action='create server snapshot')
    def server_snapshot_create(self, params: inputs.ServerSnapshotCreateInput) -> outputs.ServerSnapshotCreateOutput:
        return self.adapter.server_snapshot_create(params=params)

    @adapter_method_not_support(action='delete server snapshot')
    def server_snapshot_delete(self, params: inputs.ServerSnapshotDeleteInput) -> outputs.ServerSnapshotDeleteOutput:
        return self.adapter.server_snapshot_delete(params=params)

    @adapter_method_not_support(action='rollback server to snapshot')
    def server_rollback_snapshot(
            self, params: inputs.ServerRollbackSnapshotInput) -> outputs.ServerRollbackSnapshotOutput:
        return self.adapter.server_rollback_snapshot(params=params)


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

    def get_vpn(self, username: str, **kwargs):
        return self.adapter.get_vpn(username=username)

    def create_vpn(self, username: str, password: str = None, who_action: str = None, **kwargs):
        return self.adapter.create_vpn(username=username, password=password, who_action=who_action)

    def get_vpn_or_create(self, username: str, who_action: str = None, **kwargs):
        return self.adapter.get_vpn_or_create(username=username, who_action=who_action)

    def vpn_change_password(self, username: str, password: str, who_action: str = None, **kwargs):
        return self.adapter.vpn_change_password(username=username, password=password, who_action=who_action)

    def get_vpn_config_file_url(self, *args, **kwargs):
        return self.adapter.get_vpn_config_file_url()

    def get_vpn_ca_file_url(self, *args, **kwargs):
        return self.adapter.get_vpn_ca_file_url()

    def active_vpn(self, username: str, who_action: str = None, **kwargs):
        return self.adapter.vpn_active(username=username, who_action=who_action)

    def deactive_vpn(self, username: str, who_action: str = None, **kwargs):
        return self.adapter.vpn_deactive(username=username, who_action=who_action)
