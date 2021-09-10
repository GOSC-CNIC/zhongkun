from datetime import datetime, timedelta, timezone
import uuid
import re
from pytz import utc

import openstack
from openstack import exceptions as opsk_exceptions

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs

from adapters import exceptions
from adapters.params import ParamsName


datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


def get_fixed_timezone(offset):
    """Return a tzinfo instance with a fixed offset from UTC."""
    if isinstance(offset, timedelta):
        offset = offset.total_seconds() // 60
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return timezone(timedelta(minutes=offset), name)


def parse_datetime(value):
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Return None if the input isn't well formatted.
    """
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        kw['microsecond'] = kw['microsecond'] and kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)


def iso_to_datetime(value, default=datetime(year=1, month=1, day=1, hour=0, minute=0, second=0, tzinfo=utc)):
    try:
        parsed = parse_datetime(value)
        if parsed is not None:
            return default
    except (ValueError, TypeError):
        return default


class OpenStackAdapter(BaseAdapter):
    """
    OpenStack服务API适配器
    """

    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = '1.0',
                 **kwargs
                 ):
        api_version = api_version if api_version in ['1.0', '2.0'] else '1.0'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth, **kwargs)

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs):
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()

        :raises: AuthenticationFailed, Error
        """
        username = params.username
        password = params.password
        auth_url = self.endpoint_url
        region = self.kwargs.get(ParamsName.REGION, 'RegionOne')
        project_name = self.kwargs.get(ParamsName.PROJECT_NAME, 'admin')
        user_domain = self.kwargs.get(ParamsName.USER_DOMAIN_NAME, 'default')
        project_domain = self.kwargs.get(ParamsName.PROJECT_DOMAIN_NAME, 'default')

        try:
            connect = openstack.connect(
                auth_url=auth_url,
                project_name=project_name,
                username=username,
                password=password,
                region_name=region,
                user_domain_name=user_domain,
                project_domain_name=project_domain,
                app_name='examples',
                app_version=self.api_version,
            )
            connect.compute         # Test whether the connection is successful
            expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()
            auth = outputs.AuthenticateOutput(style='token', token='', header=None, query=None,
                                              expire=int(expire), username=username, password=password,
                                              vmconnect=connect)
        except Exception as e:
            raise exceptions.AuthenticationFailed(message=str(e))

        self.auth = auth
        return auth

    def _get_openstack_connect(self) -> openstack.connection.Connection:
        return self.auth.kwargs['vmconnect']

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            flavor = self.get_or_create_flavor(params.ram, params.vcpu)
            server_re = service_instance.compute.create_server(
                name='gosc-instance-'+str(uuid.uuid1()), image_id=params.image_id, flavor_id=flavor.id,
                networks=[{"uuid": params.network_id}])

            server = outputs.ServerCreateOutputServer(
                uuid=server_re.id
            )
            return outputs.ServerCreateOutput(server=server)
        except Exception as e:
            return outputs.ServerCreateOutput(ok=False, error=exceptions.Error(str(e)), server=None)

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        try:
            service_instance = self._get_openstack_connect()
            server = service_instance.compute.get_server(params.server_id)
            try:
                addresses = server.addresses
                server_ip = {'ipv4': addresses[list(addresses.keys())[0]][0]['addr'], 'public_ipv4': None}
            except Exception as e:
                server_ip = {'ipv4': '', 'public_ipv4': None}

            ip = outputs.ServerIP(**server_ip)
            image_temp = service_instance.image.get_image(server.image.id)

            image = outputs.ServerImage(
                _id=server.image.id,
                name=image_temp.name,
                system=image_temp.properties['os'],
                desc=''
            )

            flavor = server.flavor
            server = outputs.ServerDetailOutputServer(
                uuid=server.id,
                ram=flavor['ram'],
                vcpu=flavor['vcpus'],
                ip=ip,
                image=image,
                creation_time=iso_to_datetime(server.created_at),
                default_user='',
                default_password=''
            )
            return outputs.ServerDetailOutput(server=server)
        except exceptions.Error as e:
            return outputs.ServerDetailOutput(ok=False, error=exceptions.Error('server detail failed'), server=None)

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            service_instance.compute.delete_server(params.server_id, force=True)
            return outputs.ServerDeleteOutput()
        except Exception as e:
            return outputs.ServerDeleteOutput(ok=False, error=exceptions.Error(message=f'Failed to delete server, {str(e)}'))

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            if params.action == inputs.ServerAction.START:
                service_instance.compute.start_server(params.server_id)
            elif params.action == inputs.ServerAction.SHUTDOWN:
                service_instance.compute.stop_server(params.server_id)
            elif params.action == inputs.ServerAction.DELETE:
                service_instance.compute.delete_server(params.server_id)
            elif params.action == inputs.ServerAction.DELETE_FORCE:
                service_instance.compute.delete_server(params.server_id, force=True)
            elif params.action == inputs.ServerAction.POWER_OFF:
                service_instance.compute.stop_server(params.server_id)
            elif params.action == inputs.ServerAction.REBOOT:
                service_instance.compute.reboot_server(params.server_id, 'HARD')
            else:
                return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))
            return outputs.ServerActionOutput()
        except Exception as e:
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        service_instance = self._get_openstack_connect()
        status_map = {
            'ACTIVE': outputs.ServerStatus.RUNNING,
            'UNKNOWN': outputs.ServerStatus.NOSTATE,
            'PAUSED': outputs.ServerStatus.PAUSED,
            'SHUTOFF': outputs.ServerStatus.SHUTDOWN,
            'SUSPENDED': outputs.ServerStatus.PMSUSPENDED
        }
        try:
            server = service_instance.compute.get_server(params.server_id)
            if server is None:
                status_code = outputs.ServerStatus.MISS
            else:
                status = server.status
                if status in status_map:
                    status_code = status_map[status]
                else:
                    status_code = outputs.ServerStatus.NOSTATE
        except opsk_exceptions.ResourceNotFound as e:
            status_code = outputs.ServerStatus.MISS
        except Exception as e:
            return outputs.ServerStatusOutput(
                ok=False, error=exceptions.Error(f'get server status failed, {str(e)}'),
                status=outputs.ServerStatus.NOSTATE, status_mean='')

        if status_code not in outputs.ServerStatus():
            status_code = outputs.ServerStatus.NOSTATE
        status_mean = outputs.ServerStatus.get_mean(status_code)
        return outputs.ServerStatusOutput(status=status_code, status_mean=status_mean)

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        try:
            service_instance = self._get_openstack_connect()
            server = service_instance.compute.get_server(params.server_id)
            console = service_instance.compute.create_server_remote_console(
                server, protocol='vnc', type='novnc')
            vnc_url = console.url
            port_pos = vnc_url.find(':', 7)
            if port_pos != -1:
                vnc_url = self.endpoint_url + vnc_url[port_pos:len(vnc_url)]
            return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=vnc_url))
        except Exception as e:
            return outputs.ServerVNCOutput(
                ok=False, error=exceptions.Error(f'get vnc failed, {str(e)}'), vnc=None)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            result = []
            for image in service_instance.image.images():
                image_name = image.name
                desc = image.properties.get('description', '')
                system = image.properties.get('os')
                if not system:
                    system = image_name

                img_obj = outputs.ListImageOutputImage(id=image.id, name=image_name, system=system, desc=desc,
                                                       system_type=image.os_type, creation_time=image.created_at,
                                                       default_username='', default_password=''
                                                       )
                result.append(img_obj)
            return outputs.ListImageOutput(images=result)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error(f'list image failed, {str(e)}'), images=[])

    def get_or_create_flavor(self, ram: int, vcpu: int):
        service_instance = self._get_openstack_connect()
        flavors = service_instance.compute.flavors()
        for flavor in flavors:
            if flavor.ram == ram and flavor.vcpus == vcpu:
                return flavor

        flavor = service_instance.compute.create_flavor("flavor" + str(len(flavors)), ram, vcpu, 2)
        return flavor

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        service_instance = self._get_openstack_connect()
        try:
            result = []
            for net in service_instance.network.networks():
                public = False
                subnet = service_instance.network.get_subnet(net.subnet_ids[0])
                new_net = outputs.ListNetworkOutputNetwork(id=net.id, name=net.name, public=public,
                                                           segment=subnet.cidr)
                result.append(new_net)
            return outputs.ListNetworkOutput(networks=result)
        except Exception as e:
            return outputs.ListNetworkOutput(ok=False, error=exceptions.Error('list networks failed'), networks=[])

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        try:
            service_instance = self._get_openstack_connect()
            network = service_instance.network.get_network(params.network_id)
            subnet = service_instance.network.get_subnet(network.subnet_ids[0])
            new_net = outputs.NetworkDetail(id=params.network_id, name=network.name,
                                            public=False, segment=subnet.cidr)
            return outputs.NetworkDetailOutput(network=new_net)
        except Exception as e:
            return outputs.NetworkDetailOutput(ok=False, error=exceptions.Error(str(e)), network=None)

    def create_volume(self, params: inputs.VolumeCreateInput, **kwargs):
        """
        Create a new volume.
        """
        try:
            service_instance = self._get_openstack_connect()
            volume = service_instance.volume.create_volume(
                size=params.size,
                description=params.description
            )
        except Exception as e:
            pass
