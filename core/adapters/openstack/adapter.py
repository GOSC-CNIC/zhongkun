from datetime import datetime, timedelta, timezone
import uuid
import re
import base64
import string
import random

from django.core.paginator import Paginator
import openstack
from openstack import exceptions as opsk_exceptions
from keystoneauth1.exceptions import EndpointNotFound

from ..base import BaseAdapter
from .. import inputs, outputs, exceptions
from ..params import OpenStackParams


datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


def random_string(length: int = 8):
    letters = string.ascii_letters + string.digits
    items = [random.choice(letters) for _ in range(length)]
    return ''.join(items)


def build_user_data(username: str = 'root', password: str = 'cnic.cn'):
    sh = f"#!/bin/bash\npasswd {username}<<EOF\n{password}\n{password}\nEOF\n" \
         f"sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/g' /etc/ssh/sshd_config\nservice ssh restart\n"
    sh = base64.b64encode(sh.encode('utf-8'))
    return sh.decode('utf-8')


def get_admin_pass_form_user_data(user_data: str):
    """
    :return: tuple(str, str)
        username, password
    """
    try:
        sh = base64.b64decode(user_data.encode('utf-8'))
        sh = sh.decode(encoding='utf-8')
        lines = sh.splitlines()
        index = -1
        for i, v in enumerate(lines):
            if v.startswith('passwd') and v.endswith('<<EOF'):
                index = i
                break

        if index < 0:
            return '', ''

        line = lines[index]
        line = line.rstrip('<<EOF')
        line = line.lstrip('passwd ')
        user = line.strip(' ')
        password = lines[index + 1]
        if password != lines[index + 2]:
            password = ''

        return user, password
    except Exception as e:
        return '', ''


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
            tzinfo = timezone.utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)


def iso_to_datetime(value, default=datetime(year=1, month=1, day=1, hour=0, minute=0, second=0, tzinfo=timezone.utc)):
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
        region = self.kwargs.get(OpenStackParams.REGION, 'RegionOne')
        project_name = self.kwargs.get(OpenStackParams.PROJECT_NAME, 'admin')
        user_domain = self.kwargs.get(OpenStackParams.USER_DOMAIN_NAME, 'default')
        project_domain = self.kwargs.get(OpenStackParams.PROJECT_DOMAIN_NAME, 'default')

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
            connect.authorize()  # Test whether the connection is successful
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

    @staticmethod
    def _build_instance_name(uid: str):
        return f'gosc-instance-{uid}'

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        admin_user = 'root'
        admin_pass = random_string()
        user_data = build_user_data(username=admin_user, password=admin_pass)
        conn = self._get_openstack_connect()
        try:
            if params.systemdisk_size:
                if params.systemdisk_size < self.SYSTEM_DISK_MIN_SIZE_GB:
                    return outputs.ServerCreateOutput(
                        ok=False, error=exceptions.Error(message=f'系统盘大小不能小于{self.SYSTEM_DISK_MIN_SIZE_GB} GiB'),
                        server=None)

                systemdisk_size = params.systemdisk_size
            else:
                systemdisk_size = self.SYSTEM_DISK_MIN_SIZE_GB

            instance_name = self._build_instance_name(str(uuid.uuid1()))
            flavor = self.get_or_create_flavor(params.ram, params.vcpu, systemdisk_size=systemdisk_size)
            server_re = conn.compute.create_server(
                name=instance_name, image_id=params.image_id, flavor_id=flavor.id,
                networks=[{"uuid": params.network_id}],
                user_data=user_data,
                admin_pass=admin_pass,
                config_drive=True
            )

            server = outputs.ServerCreateOutputServer(
                uuid=server_re.id, name=server_re.name, default_user=admin_user, default_password=admin_pass
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
            conn = self._get_openstack_connect()
            instance = conn.compute.get_server(params.instance_id)
            try:
                addresses = instance.addresses
                ipv4 = ''
                if addresses:
                    for name, ips in addresses.items():
                        ipv4 = ips[0]['addr']
                        break

                server_ip = {'ipv4': ipv4, 'public_ipv4': None}
            except Exception as e:
                server_ip = {'ipv4': '', 'public_ipv4': None}

            ip = outputs.ServerIP(**server_ip)
            image_temp = conn.image.get_image(instance.image.id)
            properties = {}
            if image_temp.properties:
                properties = image_temp.properties
            desc = properties.get('description', '')
            system = properties.get('os')

            image = outputs.ServerImage(
                _id=instance.image.id,
                name=image_temp.name,
                system=system,
                desc=desc
            )

            flavor = instance.flavor
            user_data = instance.user_data
            username, password = get_admin_pass_form_user_data(user_data)
            azone_id = ''
            if isinstance(instance.availability_zone, str):
                azone_id = instance.availability_zone
            server = outputs.ServerDetailOutputServer(
                uuid=instance.id,
                name=instance.name,
                ram=flavor['ram'],
                vcpu=flavor['vcpus'],
                ip=ip,
                image=image,
                creation_time=iso_to_datetime(instance.created_at),
                default_user=username,
                default_password=password,
                azone_id=azone_id,
                disk_size=flavor.get('disk', 0)
            )
            return outputs.ServerDetailOutput(server=server)
        except Exception as e:
            return outputs.ServerDetailOutput(ok=False, error=exceptions.Error('server detail failed'), server=None)

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            service_instance.compute.delete_server(params.instance_id, force=True)
            return outputs.ServerDeleteOutput()
        except Exception as e:
            return outputs.ServerDeleteOutput(ok=False,
                                              error=exceptions.Error(message=f'Failed to delete server, {str(e)}'))

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        service_instance = self._get_openstack_connect()
        instance_id = params.instance_id
        try:
            if params.action == inputs.ServerAction.START:
                service_instance.compute.start_server(instance_id)
            elif params.action == inputs.ServerAction.SHUTDOWN:
                service_instance.compute.stop_server(instance_id)
            elif params.action == inputs.ServerAction.DELETE:
                service_instance.compute.delete_server(instance_id)
            elif params.action == inputs.ServerAction.DELETE_FORCE:
                service_instance.compute.delete_server(instance_id, force=True)
            elif params.action == inputs.ServerAction.POWER_OFF:
                service_instance.compute.stop_server(instance_id)
            elif params.action == inputs.ServerAction.REBOOT:
                service_instance.compute.reboot_server(instance_id, 'HARD')
            else:
                return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))
            return outputs.ServerActionOutput()
        except Exception as e:
            message = getattr(e, 'details', '')
            if not message:
                message = f'server action failed, {str(e)}'
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error(message))

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
            'SHUTOFF': outputs.ServerStatus.SHUTOFF,
            'SUSPENDED': outputs.ServerStatus.PMSUSPENDED,
            'ERROR': outputs.ServerStatus.ERROR,
            'BUILD': outputs.ServerStatus.BUILDING,
            'REBUILD': outputs.ServerStatus.BUILDING,
            'BUILDING': outputs.ServerStatus.BUILDING,
            'DELETED': outputs.ServerStatus.MISS,
            'SOFT_DELETED': outputs.ServerStatus.MISS
        }
        try:
            server = service_instance.compute.get_server(params.instance_id)
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
            server = service_instance.compute.get_server(params.instance_id)
            console = service_instance.compute.create_server_remote_console(
                server, protocol='vnc', type='novnc')
            vnc_url = console.url
            # port_pos = vnc_url.find(':', 7)
            # if port_pos != -1:
            #     vnc_url = self.endpoint_url + vnc_url[port_pos:len(vnc_url)]
            return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=vnc_url))
        except Exception as e:
            return outputs.ServerVNCOutput(
                ok=False, error=exceptions.Error(f'get vnc failed, {str(e)}'), vnc=None)

    def server_rebuild(self, params: inputs.ServerRebuildInput, **kwargs):
        """
        重建（更换系统镜像）虚拟服务器
        :return:
            outputs.ServerRebuildOutput()
        """
        instance_id = params.instance_id
        image_id = params.image_id
        admin_user = 'root'
        admin_pass = ''
        try:
            conn = self._get_openstack_connect()
            instance_name = self._build_instance_name(str(uuid.uuid1()))
            server = conn.compute.rebuild_server(
                server=instance_id, name=instance_name, image=params.image_id, admin_password=admin_pass)
        except Exception as e:
            return outputs.ServerRebuildOutput(
                ok=False, error=exceptions.Error(f'rebuild server failed, {str(e)}'),
                instance_id=instance_id, image_id=image_id, default_user='', default_password='')

        return outputs.ServerRebuildOutput(
            instance_id=server.id, instance_name=server.name, image_id=image_id,
            default_user=admin_user, default_password=admin_pass)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        service_instance = self._get_openstack_connect()
        try:
            result = []
            # visibility in ['public', 'private', 'shared']
            images = service_instance.image.images(status='active')
            for image in images:
                if image.status and image.status.lower() != 'active':
                    continue

                # if not (image.visibility and image.visibility.lower() == 'public'):
                #     continue

                img_obj = self._output_image_obj(image)
                result.append(img_obj)
            paginator = Paginator(result, params.page_size)
            page_result = paginator.page(params.page_num).object_list
            return outputs.ListImageOutput(images=page_result, count=paginator.count)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error(f'list image failed, {str(e)}'), images=[])

    @staticmethod
    def _get_property_of_image(image, prop_name):
        openstack_property_value = None
        if 'desc' != prop_name:
            openstack_name_mapping = {'system_type': 'os_type', 'release': 'os_distro',
                                      'architecture': 'architecture', 'version': 'os_version'}
            openstack_property_value = image.get(openstack_name_mapping[prop_name], None)
        if not openstack_property_value:
            if not image.properties:
                if 'desc' == prop_name:
                    openstack_property_value = ''
                else:
                    openstack_property_value = 'Unknown'
            else:
                egi_name_mapping = {'desc': 'description', 'system_type': 'sl:os', 'release': 'sl:osname',
                                    'architecture': 'sl:arch', 'version': 'sl:osversion'}
                openstack_property_value = image.properties.get(egi_name_mapping[prop_name], 'Unknown')
                if 'desc' == prop_name and openstack_property_value == 'Unknown':
                    openstack_property_value = ''
        return str(openstack_property_value)

    def _output_image_obj(self, image):
        """
        :return: outputs.ListImageOutputImage()
        """
        image_name = image.name
        desc = self._get_property_of_image(image, 'desc')
        system_type = self._get_property_of_image(image, 'system_type')
        release = self._get_property_of_image(image, 'release')
        architecture = self._get_property_of_image(image, 'architecture')
        version = self._get_property_of_image(image, 'version')

        img_obj = outputs.ListImageOutputImage(
            _id=image.id, name=image_name, release=release, version=version, architecture=architecture, desc=desc,
            system_type=system_type,
            creation_time=image.created_at, default_username='', default_password='',
            min_sys_disk_gb=image.min_disk, min_ram_mb=image.min_ram
        )
        return img_obj

    def image_detail(self, params: inputs.ImageDetailInput, **kwargs):
        """
        查询镜像信息
        :return:
            output.ImageDetailOutput()
        """
        image_id = params.image_id
        try:
            conn = self._get_openstack_connect()
            image = conn.image.get_image(image_id)
            img_obj = self._output_image_obj(image)
            return outputs.ImageDetailOutput(image=img_obj)
        except Exception as e:
            return outputs.ImageDetailOutput(ok=False, error=exceptions.Error(f'get image failed, {str(e)}'))

    @staticmethod
    def _flavor_name(ram: int, vcpu: int, disk: int):
        return f"Ram{ram}Mb-{vcpu}vcpu-{disk}Gb"

    def get_or_create_flavor(self, ram: int, vcpu: int, systemdisk_size: int):
        name = self._flavor_name(ram=ram, vcpu=vcpu, disk=systemdisk_size)
        service_instance = self._get_openstack_connect()
        # flavor = service_instance.compute.find_flavor(name_or_id=name)
        # if flavor:
        #     return flavor
        flavors = service_instance.compute.flavors()
        for flavor in flavors:
            if flavor.ram == ram and flavor.vcpus == vcpu and flavor.disk == systemdisk_size:
                return flavor

        params = {
            'name': name,
            'ram': ram, 'vcpus': vcpu, 'disk': systemdisk_size
        }
        flavor = service_instance.compute.create_flavor(**params)
        return flavor

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        azone_id = params.azone_id
        service_instance = self._get_openstack_connect()
        try:
            result = []
            networks = service_instance.network.networks()
            for net in networks:
                public = net.is_router_external
                if azone_id:
                    if azone_id not in net.availability_zones:
                        continue

                if net.subnet_ids:
                    subnet = service_instance.network.get_subnet(net.subnet_ids[0])
                    new_net = outputs.ListNetworkOutputNetwork(_id=net.id, name=net.name, public=public,
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
            is_public = network.is_router_external
            new_net = outputs.NetworkDetail(_id=params.network_id, name=network.name,
                                            public=is_public, segment=subnet.cidr)
            return outputs.NetworkDetailOutput(network=new_net)
        except opsk_exceptions.ResourceNotFound as e:
            return outputs.NetworkDetailOutput(ok=False, error=exceptions.ResourceNotFound(str(e)), network=None)
        except Exception as e:
            return outputs.NetworkDetailOutput(
                ok=False, error=exceptions.Error(str(e), status_code=getattr(e, 'status_code', 500)), network=None)

    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput):
        try:
            conn = self._get_openstack_connect()
            a_zones = conn.compute.availability_zones()
            zones = []
            for zone in a_zones:
                name = zone.name
                available = True
                if zone.state:
                    available = bool(zone.state.get('available'))
                zones.append(outputs.AvailabilityZone(_id=name, name=name, available=available))

            return outputs.ListAvailabilityZoneOutput(zones)
        except Exception as e:
            return outputs.ListAvailabilityZoneOutput(ok=False, error=exceptions.Error(str(e)), zones=None)

    def get_quota(self, params: inputs.QuotaInput):
        """
        查询资源配额信息（可用总资源）

        :return:
            outputs.QuotaOutput()
        """
        try:
            conn = self._get_openstack_connect()
            project_id = conn.current_project_id
            cp_quota = conn.compute.get_quota_set(project=project_id)
            try:
                disk_quota = conn.volume.get_quota_set(project=project_id)
                disk_gib = getattr(disk_quota, 'gigabytes', None)
                per_disk_gib = getattr(disk_quota, 'per_volume_gigabytes', None)
                disks = getattr(disk_quota, 'volumes', None)
            except (opsk_exceptions.EndpointNotFound, EndpointNotFound) as exc:     # 没有块存储服务
                disk_gib = 0
                per_disk_gib = 0
                disks = 0

            ram = getattr(cp_quota, 'ram', None)
            if ram:
                ram = ram // 1024
            quota = outputs.Quota(
                vcpu=getattr(cp_quota, 'cores', None),
                ram_gib=ram,
                servers=getattr(cp_quota, 'instances', None),
                public_ips=None,
                private_ips=None,
                disk_gib=disk_gib,
                per_disk_gib=per_disk_gib,
                disks=disks
            )

            return outputs.QuotaOutput(ok=True, quota=quota)
        except Exception as e:
            return outputs.QuotaOutput(ok=False, error=exceptions.Error(str(e)), quota=outputs.Quota())

    def resource_statistics(self) -> outputs.ResourceStatisticsOutput:
        """
        资源统计
        """
        try:
            conn = self._get_openstack_connect()
            servers = list(conn.compute.servers(details=False, all_projects=True, vm_state='ACTIVE'))
            return outputs.ResourceStatisticsOutput(ok=True, server_count=len(servers))
        except Exception as e:
            return outputs.ResourceStatisticsOutput(ok=False, error=exceptions.Error(str(e)), server_count=0)
