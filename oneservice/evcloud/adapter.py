import requests

from ..base import AdapterBase
from .builders import APIBuilder
from . import exceptions


def get_failed_msg(response, msg_key='code_text'):
    """
    请求失败错误信息

    :param response: requests.Reponse()
    :param msg_key: 信息键值
    :return:
    """
    try:
        data =response.json()
        msg = data.get(msg_key, '')
        return msg
    except Exception:
        return ''


class EVCloudAdapter(AdapterBase):
    """
    EVCloud服务API适配器
    """
    def __init__(self,
                 endpoint_url: str,
                 auth=None,      # type tuple (username, password)
                 api_version: str = 'v3'
                 ):
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth)
        self.api_builder = APIBuilder(endpoint_url=self.endpoint_url, api_version=self.api_version)

    def authenticate(self, username, password, style: str = 'token'):
        """
        认证获取 Token

        :param username: 用户名
        :param password: 密码
        :param style: 认证类型；'token', 'jwt'
        :return:
            ['token', 'token str']
            ['jwt', 'jwt str']

        :raises: AuthenticationFailed, Error
        """
        style = style.lower()
        if style == 'jwt':
            url = self.api_builder.jwt_base_url()
        else:
            style = 'token'
            url = self.api_builder.token_base_url()

        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            data = r.json()
            if style == 'jwt':
                key = data['access']
            else:
                key = data['token']['key']
            return [style, key]

        raise exceptions.AuthenticationFailed(status_code=r.status_code)

    def server_create(self, image_id: str, flavor_id: str, region_id: str, network_id: str = None,
                      headers={}, extra_kwargs={}):
        """
        创建虚拟主机

        :param image_id: 系统镜像id
        :param flavor_id: 配置样式id
        :param region_id: 区域/分中心id
        :param network_id: 子网id
        :param headers: 标头
        :param extra_kwargs: 其他参数
        """
        image_id = int(image_id)
        vlan_id = int(network_id) if network_id else 0
        if image_id <= 0:
            raise exceptions.APIInvalidParam('invalid param "image_id"')

        data = {
            'center_id': region_id,
            'image_id': image_id,
            'flavor_id': flavor_id,
            'remarks': extra_kwargs.get('remarks', '')
        }
        if vlan_id > 0:
            data['vlan_id'] = vlan_id

        url = self.api_builder.vm_base_url()
        try:
            r = requests.post(url, data=data, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 201:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def server_delete(self, server_id, headers={}):
        url = self.api_builder.vm_detail_url(vm_uuid=server_id)
        try:
            r = requests.delete(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 204:
            return True

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def server_action(self, server_id, op, headers={}):
        """
        操作虚拟主机

        :param server_id:
        :param op:
        :param headers:
        :return:
        """
        if op not in ['start', 'reboot', 'shutdown', 'poweroff', 'delete', 'delete_force']:
            raise exceptions.APIInvalidParam('invalid param "op"')

        url = self.api_builder.vm_action_url(vm_uuid=server_id)
        try:
            r = requests.patch(url, data={'op': op}, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return True

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def server_status(self, server_id, headers={}):
        url = self.api_builder.vm_status_url(vm_uuid=server_id)
        try:
            r = requests.get(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def server_vnc(self, server_id, headers={}):
        url = self.api_builder.vm_vnc_url(vm_uuid=server_id)
        try:
            r = requests.post(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def list_images(self, region_id: str, headers={}):
        """
        列举镜像

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.image_base_url(query={'center_id': center_id, 'tag': 1})

        try:
            r = requests.get(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def list_networks(self, region_id: str, headers={}):
        """
        列举子网

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.vlan_base_url(query={'center_id': center_id})

        try:
            r = requests.get(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def list_groups(self, region_id: str, headers={}):
        """
        列举宿主机组

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.group_base_url(query={'center_id': center_id})

        try:
            r = requests.get(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def list_flavors(self, headers={}):
        """
        列举配置样式

        :param headers:
        :return:
        """
        url = self.api_builder.flavor_base_url()

        try:
            r = requests.get(url, headers=headers)
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            return r.json()

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

