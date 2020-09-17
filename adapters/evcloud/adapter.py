from datetime import datetime
import requests

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
from .builders import APIBuilder
from . import exceptions
from .validators import InputValidator
from .converters import OutputConverter


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


class EVCloudAdapter(BaseAdapter):
    """
    EVCloud服务API适配器
    """
    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = 'v3'
                 ):
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth)
        self.api_builder = APIBuilder(endpoint_url=self.endpoint_url, api_version=self.api_version)

    def get_auth_header(self):
        """
        :return: {}

        :raises: NotAuthenticated, AuthenticationFailed, Error
        """
        auth = self.auth
        now = datetime.utcnow().timestamp()
        if auth is None:
            raise exceptions.NotAuthenticated()
        elif now >= auth.expire:
            auth = self.authenticate(auth.username, auth.password)

        h = auth.header
        return {h.header_name: h.header_value}

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
            auth = self.authenticate_jwt(username=username, password=password)
        except exceptions.Error:
            auth = self.authenticate_token(username=username, password=password)

        self.auth = auth
        return auth

    def authenticate_jwt(self, username, password):
        url = self.api_builder.jwt_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            raise exceptions.Error(str(e))

        if r.status_code == 200:
            data = r.json()
            token = data['access']
            return OutputConverter.to_authenticate_output_jwt(token=token, username=username, password=password)

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
            return OutputConverter.to_authenticate_output_token(token=token, username=username, password=password)

        raise exceptions.AuthenticationFailed(status_code=r.status_code)

    def server_create(self, params: inputs.CreateServerInput, **kwargs):
        """
        创建虚拟主机
        :return:
            outputs.CreateServerOutput()
        """
        data = InputValidator.create_server_validate(params)
        headers = self.get_auth_header()
        url = self.api_builder.vm_base_url()
        r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        rj = r.json()
        return OutputConverter.to_create_server_output(rj['vm'])

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

    def vpn_change_password(self, username: str, password: str, headers: dict = None):
        url = self.api_builder.vpn_detail_url(username=username, query={'password': password})
        r = self.do_request(method='patch', url=url, headers=headers)
        return r.json()

    def get_vpn_config_file_url(self, **kwargs):
        return self.api_builder.vpn_config_file_url()

    def get_vpn_ca_file_url(self, **kwargs):
        return self.api_builder.vpn_ca_file_url()

    def get_network(self, network_id, headers: dict = None):
        """
        查询子网信息

        :param network_id: str or int
        :param headers:
        :return:
        """
        url = self.api_builder.vlan_detail_url(pk=network_id)
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()

    def get_flavor(self, flavor_id, headers: dict = None):
        """
        查询配置样式

        :param flavor_id:
        :param headers:
        :return:
        """
        url = self.api_builder.flavor_detail_url(pk=flavor_id)
        r = self.do_request(method='get', url=url, headers=headers)
        return r.json()
