from datetime import datetime, timedelta
import requests
import base64
import json

from ..base import BaseAdapter, AuthClass, AuthHeaderClass, AuthQueryClass
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


def base64url_decode(data):
    if isinstance(data, str):
        data = data.encode('ascii')

    rem = len(data) % 4

    if rem > 0:
        data += b'=' * (4 - rem)

    return base64.urlsafe_b64decode(data)


def get_exp_jwt(jwt: str):
    """
    从jwt获取过期时间expire
    :param jwt:
    :return:
        int     # timestamp
        0       # if error
    """
    jwt = jwt.encode('utf-8')

    try:
        signing_input, crypto_segment = jwt.rsplit(b'.', 1)
        header_segment, payload_segment = signing_input.split(b'.', 1)
    except ValueError:
        return 0

    try:
        payload = base64url_decode(payload_segment)
    except Exception:
        return 0

    payload = json.loads(payload.decode('utf-8'))
    if 'exp' not in payload:
        return 0

    try:
        return int(payload['exp'])
    except:
        return 0


class EVCloudAdapter(BaseAdapter):
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

    @staticmethod
    def do_request(method: str, url: str, ok_status_codes=(200,), headers=None, **kwargs):
        """
        :param method: 'get', 'post, 'put', 'delete', 'patch', ..
        :param ok_status_codes: 表示请求成功的状态码列表，返回响应体，其他抛出Error
        :param url:
        :param headers:
        :param kwargs:
        :return:
            requests.Response()
        :raises: Error, AuthenticationFailed, APIError
        """
        try:
            r = requests.request(method=method, url=url, headers=headers, **kwargs)
        except Exception as e:
            raise exceptions.Error(str(e))

        if not isinstance(ok_status_codes, (list, tuple)):
            ok_status_codes = [ok_status_codes]

        if r.status_code in ok_status_codes:
            return r

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed()

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def authenticate(self, username, password):
        """
        认证获取 Token

        :param username: 用户名
        :param password: 密码
        :return:


        :raises: AuthenticationFailed, Error
        """
        try:
            return self.authenticate_jwt(username=username, password=password)
        except exceptions.Error:
            pass

        return self.authenticate_token(username=username, password=password)

    def authenticate_jwt(self, username, password):
        url = self.api_builder.jwt_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            data = r.json()
            token = data['access']
            expire = get_exp_jwt(token) - 60    # 过期时间提前60s
            if expire < 0:
                expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()

            header = AuthHeaderClass(header_name='Authorization', header_value=f'JWT {token}')
            auth = AuthClass(style='JWT', token=token, header=header, query=None, expire=expire)
            return auth

        raise exceptions.AuthenticationFailed(status_code=r.status_code)

    def authenticate_token(self, username, password):
        url = self.api_builder.token_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            data = r.json()
            token = data['token']['key']
            expire = (datetime.utcnow() + timedelta(hours=2)).timestamp()
            header = AuthHeaderClass(header_name='Authorization', header_value=f'Token {token}')
            auth = AuthClass(style='token', token=token, header=header, query=None, expire=expire)
            return auth

        raise exceptions.AuthenticationFailed(status_code=r.status_code)

    def server_create(self, image_id: str, flavor_id: str, region_id: str, network_id: str = None,
                      headers: dict = None, extra_kwargs: dict = None):
        """
        创建虚拟主机

        :param image_id: 系统镜像id
        :param flavor_id: 配置样式id
        :param region_id: 区域/分中心id
        :param network_id: 子网id
        :param headers: 标头
        :param extra_kwargs: 其他参数
        """
        if extra_kwargs is None:
            extra_kwargs = {}

        image_id = int(image_id)
        vlan_id = int(network_id) if network_id else 0
        if image_id <= 0:
            raise exceptions.APIInvalidParam('invalid param "image_id"')

        data = {
            'center_id': region_id,
            'image_id': image_id,
            'flavor_id': flavor_id,
            'remarks': extra_kwargs.get('remarks', 'GOSC')
        }
        if vlan_id > 0:
            data['vlan_id'] = vlan_id

        url = self.api_builder.vm_base_url()
        r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        return r.json()

    def server_delete(self, server_id, headers: dict = None):
        url = self.api_builder.vm_detail_url(vm_uuid=server_id)
        r = self.do_request(method='delete', url=url, ok_status_codes=[204], headers=headers)
        return True

    def server_action(self, server_id, op, headers: dict = None):
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
        r = self.do_request(method='patch', url=url, data={'op': op}, headers=headers)
        return True

    def server_status(self, server_id, headers: dict = None):
        url = self.api_builder.vm_status_url(vm_uuid=server_id)
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def server_vnc(self, server_id, headers: dict = None):
        url = self.api_builder.vm_vnc_url(vm_uuid=server_id)
        r = self.do_request(method='post', url=url, headers=headers)
        return r.json()

    def list_images(self, region_id: str, headers: dict = None):
        """
        列举镜像

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.image_base_url(query={'center_id': center_id, 'tag': 1})
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def list_networks(self, region_id: str, headers: dict = None):
        """
        列举子网

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.vlan_base_url(query={'center_id': center_id})
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def list_groups(self, region_id: str, headers: dict = None):
        """
        列举宿主机组

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        center_id = int(region_id)
        url = self.api_builder.group_base_url(query={'center_id': center_id})
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def list_flavors(self, headers: dict = None):
        """
        列举配置样式

        :param headers:
        :return:
        """
        url = self.api_builder.flavor_base_url()
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def get_vpn(self, username: str, headers: dict = None):
        url = self.api_builder.vpn_detail_url(username=username)
        r = self.do_request(method='get', url=url, ok_status_codes=[200], headers=headers)
        return r.json()

    def create_vpn(self, username: str, password: str = None, headers: dict = None):
        data = {'username': username}
        if password:
            data['password'] = password

        url = self.api_builder.vpn_base_url()
        r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        return r.json()

    def get_vpn_or_create(self, username: str, headers: dict = None):
        url = self.api_builder.vpn_detail_url(username=username)
        r = self.do_request(method='get', url=url, ok_status_codes=[200, 404], headers=headers)
        d = r.json()
        if r.status_code == 200:
            return d

        if 'err_code' in d and d['err_code'] == 'NoSuchVPN':
            return self.create_vpn(username=username, headers=headers)

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def get_vpn_config_file_url(self, **kwargs):
        return self.api_builder.vpn_config_file_url()

    def get_vpn_ca_file_url(self, **kwargs):
        return self.api_builder.vpn_ca_file_url()
