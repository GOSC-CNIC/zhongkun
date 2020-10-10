from datetime import datetime, timedelta, timezone
import requests

import uuid
import re
from pytz import utc


from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
import time

from adapters import exceptions

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
                 api_version: str = 'v3'
                 ):
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth)

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs):
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()

        :raises: AuthenticationFailed, Error
        """
        username = params.username
        password = params.password
        url = self.endpoint_url + ':5000/v3/auth/tokens'
        auth_data = {"auth": {
            "identity": {
                "methods": ["password"],
                "password": {
                    "user": {
                        "name": username,
                        "domain": {"id": "default"},
                        "password": password
                    }
                }
            },
            "scope": {
                "project": {
                    "name": "admin",
                    "domain": {"id": "default"}
                }
            }
        }
        }
        try:
            r = requests.post(url, json=auth_data)
            if r.status_code == 201:
                token = r.headers['X-Subject-Token']
                expired_at = r.json()['token']['expires_at']
                expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()
                header = outputs.AuthenticateOutputHeader(header_name='X-Auth-Token', header_value=token)
                auth = outputs.AuthenticateOutput(style='token', token=token, header=header, query=None,
                                                  expire=int(expire), username=username, password=password)
            else:
                raise exceptions.AuthenticationFailed()
        except Exception as e:
            raise exceptions.AuthenticationFailed()

        self.auth = auth
        return auth

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        headers = {self.auth.header.header_name:self.auth.header.header_value}
        server_url = self.endpoint_url + ':8774/v2.1/servers'

        try:
            flavor_ref = self.get_or_create_flavor(params.ram, params.vcpu)
            server_data = {
                "server": {
                    "name": 'gosc-instance-'+str(uuid.uuid4()),
                    "imageRef": params.image_id,
                    "flavorRef": flavor_ref,
                    "networks": [{
                        "uuid": params.network_id
                    }]
                }
            }

            r = requests.post(server_url, headers=headers, json=server_data)
            server_id = r.json()['server']['id']
            server = outputs.ServerCreateOutputServer(
                uuid=server_id
            )
            return outputs.ServerCreateOutput(server=server)
        except Exception as e:
            return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('server created failed'), server=None)

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        try:
            headers = {self.auth.header.header_name: self.auth.header.header_value}
            server_url = self.endpoint_url + ':8774/v2.1/servers'

            r = requests.get(server_url + '/' + params.server_id, headers=headers)
            server_temp = r.json()['server']
            try:
                adresses = server_temp['addresses']
                server_ip = {'ipv4': adresses[list(adresses.keys())[0]][0]['addr'], 'public_ipv4': None}
            except Exception as e:
                server_ip = {'ipv4': 'ip not exist', 'public_ipv4': None}

            ip = outputs.ServerIP(**server_ip)
            image_temp=self.get_image(server_temp['image']['id'])

            image = outputs.ServerImage(
                name=image_temp['name'],
                system=image_temp['os']
            )

            flavor=self.get_flaor(server_temp['flavor']['id'])
            server = outputs.ServerDetailOutputServer(
                uuid=server_temp['id'],
                ram=flavor['flavor']['ram'],
                vcpu=flavor['flavor']['vcpus'],
                ip=ip,
                image=image,
                creation_time=iso_to_datetime(server_temp['created'])
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
        url = self.endpoint_url + ':8774/v2.1/servers/' + params.server_id + '/action'
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        command = {
            "forceDelete": None
        }
        try:
            print(url)
            r = requests.post(url, headers=headers, json=command)
            status = r.json()['server']['status']
            return None
        except Exception as e:
            raise e

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        url = self.endpoint_url + ':8774/v2.1/servers/' + params.server_id + '/action'
        headers = {self.auth.header.header_name:self.auth.header.header_value}
        command = None
        if params.action == inputs.ServerAction.START:
            command = {
                "os-start": None
            }
        elif params.action == inputs.ServerAction.SHUTDOWN:
            command = {
                "os-stop": None
            }
        elif params.action == inputs.ServerAction.DELETE:
            command = {
                "restore": None
            }
        elif params.action == inputs.ServerAction.DELETE_FORCE:
            command = {
                "forceDelete": None
            }
        elif params.action == inputs.ServerAction.POWER_OFF:
            command = {
                "os-stop": None
            }
        elif params.action == inputs.ServerAction.REBOOT:
            command = {
                "reboot": {
                    "type": "HARD"
                }
            }
        else:
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))

        try:
            print(url)
            r = requests.post(url, headers=headers, json=command)
            if r.status_code != 202:
                return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))
            return outputs.ServerActionOutput()
        except Exception as e:
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        url = self.endpoint_url + ':8774/v2.1/servers/' + params.server_id
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        status_map = {
            'ACTIVE': 1,
            'UNKNOWN': 0,
            'PAUSED': 3,
            'SHUTOFF': 4,
            'SUSPENDED': 7
        }
        try:
            print(url)
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                return outputs.ServerStatusOutput(ok=False, error=exceptions.Error('get server status failed'))
            status = r.json()['server']['status']
            status_code = status_map[status]
            if status_code not in outputs.ServerStatus():
                status_code = outputs.ServerStatus.NOSTATE
            status_mean = outputs.ServerStatus.get_mean(status_code)
            return outputs.ServerStatusOutput(status=status_code, status_mean=status_mean)
        except Exception as e:
            return outputs.ServerStatusOutput(ok=False, error=exceptions.Error('get server status failed'))

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        url = self.endpoint_url + ':8774/v2.1/servers/' + params.server_id + '/action'
        headers = {self.auth.header.header_name:self.auth.header.header_value}
        command = {
            "os-getVNCConsole": {
                "type": "novnc"
            }
        }
        try:
            print(url)
            r = requests.post(url, headers=headers, json=command)
            if r.status_code != 200:
                return outputs.ServerVNCOutput(ok=False, error=exceptions.Error('get vnc failed'), vnc=None)
            vnc_url = r.json()['console']['url']
            port_pos = vnc_url.find(':', 7)
            if port_pos != -1:
                vnc_url = self.endpoint_url + vnc_url[port_pos:len(vnc_url)]
            print(vnc_url)
            return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=vnc_url))
        except Exception as e:
            return outputs.ServerVNCOutput(ok=False, error=exceptions.Error('get vnc failed'), vnc=None)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        url = self.endpoint_url + ':9292/v2.1/images'
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        try:
            print(url)
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                return outputs.ListImageOutput(ok=False, error=exceptions.Error('list image failed'), images=[])
            images = r.json()['images']
            result = []
            for image in images:
                img_obj = outputs.ListImageOutputImage(id=image['id'], name=image['name'], system=image['os'],
                                                       desc=image['description'],
                                                       system_type=image['os_type'], creation_time=image['created_at'])
                result.append(img_obj)
            return outputs.ListImageOutput(images=result)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error('list image failed'), images=[])

    def get_image(self, image_id):
        url = self.endpoint_url + ':9292/v2.1/images/' + image_id
        headers = {self.auth.header.header_name:self.auth.header.header_value}
        try:
            print(url)
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                raise exceptions.Error('get image failed')
            image = r.json()
            return image
        except Exception as e:
            raise exceptions.Error('get image failed')

    def get_flaor(self, flavor_id):
        url = self.endpoint_url + ':8774/v2.1/flavors/' + flavor_id
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        try:
            print(url)
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                raise exceptions.Error('get flavor failed')
            image = r.json()
            return image
        except Exception as e:
            raise exceptions.Error('get flavor failed')

    def get_or_create_flavor(self, ram: int, vcpu: int):
        flavor_url = self.endpoint_url + ':8774/v2.1/flavors/detail'
        flavor_url_create = self.endpoint_url + ':8774/v2.1/flavors'
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        r = requests.get(flavor_url, headers=headers)
        if r.status_code != 200:
            raise exceptions.Error('get flavor failed')
        flavors = r.json()['flavors']
        flavor_ref = None
        for flavor in flavors:
            if flavor['ram'] == ram and flavor['vcpus'] == vcpu:
                flavor_ref = flavor['links'][1]['href']
        if flavor_ref is None:
            flavor_data = {
                "flavor": {
                    "name": "flavor" + str(len(flavors)),
                    "ram": ram,
                    "vcpus": vcpu,
                    "disk": 2
                }
            }
            r = requests.post(flavor_url_create, headers=headers, json=flavor_data)
            if r.status_code != 200:
                raise exceptions.Error('create flavor failed')
            flavor_ref = r.json()['flavor']['links'][1]['href']
        return flavor_ref

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        network_url = self.endpoint_url + ':9696/v2.0/networks'
        headers = {self.auth.header.header_name: self.auth.header.header_value}
        try:
            r = requests.get(network_url, headers=headers)
            if r.status_code != 200:
                raise exceptions.Error('list networks failed')
            networks = r.json()['networks']
            result=[]
            for net in networks:
                public = False
                new_net = outputs.ListNetworkOutputNetwork(id=net['id'], name=net['name'], public=public,
                                                           segment='123')
                result.append(new_net)
            return outputs.ListNetworkOutput(networks=result)
        except Exception as e:
            return outputs.ListNetworkOutput(ok=False, error=exceptions.Error('list networks failed'), networks=[])

    def get_network(self, network_id, headers: dict = None):
        network_url = self.endpoint_url + ':9696/v2.1/networks/' + network_id
        headers = self.auth.header
        try:
            r = requests.get(network_url, headers=headers)
            detail = r.json()['network']
            return detail
        except Exception as e:
            raise e
