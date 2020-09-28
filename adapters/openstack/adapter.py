from datetime import datetime, timedelta, timezone
import requests

import uuid

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
import time

from adapters import exceptions


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

    def authenticate(self, username, password):
        """
        认证获取 Token

        :param username: 用户名
        :param password: 密码
        :return:


        :raises: AuthenticationFailed, Error
        """
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
            r = requests.get(server_url + '/' + server_id, headers=headers)
            server_created = r.json()['server']
            adresses = r.json()['server']['addresses']
            num = 0
            while len(adresses) <= 0 and num <= 20:
                time.sleep(1)
                r = requests.get(server_url + '/' + server_id, headers=headers)
                server_created = r.json()['server']
                adresses = r.json()['server']['addresses']
                num = num + 1

            if len(adresses) == 0:
                return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('server created failed'))
            r_image = self.get_image(server_created['image']['id'])
            image = outputs.ServerCreateOutputServerImage(
                name=r_image['name'],
                system=r_image['os']
            )
            ip = outputs.ServerCreateOutputServerIP(
                ipv4=adresses[list(adresses.keys())[0]][0]['addr'],
                public_ipv4=False
            )
            server = outputs.ServerCreateOutputServer(
                uuid=server_created['id'],
                ram=params.ram,
                vcpu=params.vcpu,
                ip=ip,
                image=image,
                creation_time=server_created['created'],
                name=server_created['name']
            )
            return outputs.ServerCreateOutput(server=server)
        except Exception as e:
            return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('server created failed'), server=None)

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


# adapter = OpenstackAdapter('http://10.0.200.215')
# adapter.authenticate('admin', '123456')
# adapter.list_networks('1')
# images = adapter.list_images(params=None)
# server = inputs.ServerStatusInput('920dca92-e974-40c9-90ac-108da39f5256')
# status = adapter.server_status(server)
# vnc = adapter.server_vnc(server)
# # adapter.create_flavor()
#
# server_data = inputs.ServerCreateInput(2000, 2, network_id='df44279f-5218-4a04-95f0-8746e7a8df87', remarks='xxxx',
#                                        image_id='378bc843-4a08-41fe-8de3-88210b6ee273')
# adapter.server_create(server_data)
# print(status)

# curl  -s \
#   -H "X-Auth-Token: gAAAAABfaV0wbjGKxz7EcFyAI-NgmzTGxc1qdSMIACpQtAfrPAfnntaJpfG07uOgdhaQf7OpfC3e75UhGQk3CAN0bBNZYq4K3hOo5HNYI1BCZTrzVc8G73_Dk2MImEvUMETWSXcOO2mH3f2UBo_N7hiav32JpC-AS5XVlSAlUg5Qa_d6q993ZuU" \
#   "http://10.0.200.215:9292/v2.1/images"; echo
