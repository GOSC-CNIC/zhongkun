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
    adapter_name = 'EVCloud adapter'

    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = 'v3'
                 ):
        api_version = api_version.lower()
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
            outputs.AuthenticateOutput()
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
            return OutputConverter().to_authenticate_output_error(error=exceptions.Error(str(e)), style='jwt')

        if r.status_code == 200:
            data = r.json()
            token = data['access']
            return OutputConverter.to_authenticate_output_jwt(token=token, username=username, password=password)

        err = exceptions.AuthenticationFailed(status_code=r.status_code)
        return OutputConverter().to_authenticate_output_error(error=err, style='jwt')

    def authenticate_token(self, username, password):
        url = self.api_builder.token_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password})
        except Exception as e:
            return OutputConverter().to_authenticate_output_error(error=exceptions.Error(str(e)), style='token')

        if r.status_code == 200:
            data = r.json()
            token = data['token']['key']
            return OutputConverter.to_authenticate_output_token(token=token, username=username, password=password)

        err = exceptions.AuthenticationFailed(status_code=r.status_code)
        return OutputConverter().to_authenticate_output_error(error=err, style='token')

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟主机
        :return:
            outputs.ServerCreateOutput()
        """
        url = self.api_builder.vm_base_url()
        try:
            data = InputValidator.create_server_validate(params)
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        except exceptions.Error as e:
            return OutputConverter.to_server_create_output_error(error=e)

        rj = r.json()
        return OutputConverter.to_server_create_output(rj['vm'])

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        url = self.api_builder.vm_detail_url(vm_uuid=params.server_id, query={'force': True})
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='delete', url=url, ok_status_codes=[204, 400, 404], headers=headers)
        except exceptions.Error as e:
            return outputs.ServerDeleteOutput(ok=False, error=e)

        if r.status_code == 200:
            return outputs.ServerDeleteOutput()

        rj = r.json()
        err_code = rj.get('err_code')
        if err_code and err_code == "VmNotExist":
            return outputs.ServerDeleteOutput()

        msg = get_failed_msg(r)
        return outputs.ServerDeleteOutput(ok=False, error=exceptions.APIError(message=msg, status_code=r.status_code))

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput
        """
        action = params.action
        if action not in inputs.ServerAction.values:
            return outputs.ServerActionOutput(ok=False, error=exceptions.APIInvalidParam('invalid param "action"'))

        if action in [inputs.ServerAction.DELETE_FORCE, inputs.ServerAction.DELETE]:
            r = self.server_delete(params=inputs.ServerDeleteInput(server_id=params.server_id))
            if r.ok:
                return outputs.ServerActionOutput()

            return outputs.ServerActionOutput(ok=False, error=r.error)

        try:
            url = self.api_builder.vm_action_url(vm_uuid=params.server_id)
            headers = self.get_auth_header()
            r = self.do_request(method='patch', url=url, data={'op': action}, headers=headers)
        except exceptions.Error as e:
            return outputs.ServerActionOutput(ok=False, error=e)

        return outputs.ServerActionOutput()

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        url = self.api_builder.vm_status_url(vm_uuid=params.server_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, ok_status_codes=[200, 400, 404], headers=headers)
        except exceptions.Error as e:
            return OutputConverter.to_server_status_output_error(error=e)

        rj = r.json()
        if r.status_code == 200:
            status_code = rj['status']['status_code']
            return OutputConverter.to_server_status_output(status_code)

        err_code = rj.get('err_code')
        if err_code and err_code == "VmNotExist":
            return OutputConverter.to_server_status_output(outputs.ServerStatus.MISS)

        msg = get_failed_msg(r)
        error = exceptions.APIError(message=msg, status_code=r.status_code)
        return OutputConverter.to_server_status_output_error(error=error)

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        url = self.api_builder.vm_vnc_url(vm_uuid=params.server_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_server_vnc_output_error(error=e)

        rj = r.json()
        return OutputConverter().to_server_vnc_output(url=rj['vnc']['url'])

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            outputs.ListImageOutput()
        """
        center_id = int(params.region_id)
        url = self.api_builder.image_base_url(query={'center_id': center_id, 'tag': 1})
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_list_image_output_error(error=e)
        rj = r.json()
        return OutputConverter().to_list_image_output(rj['results'])

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:    outputs.ListNetworkOutput()
        """
        center_id = int(params.region_id)
        url = self.api_builder.vlan_base_url(query={'center_id': center_id})
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_list_network_output_error(error=e)

        rj = r.json()
        return OutputConverter().to_list_network_output(networks=rj['results'])

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

    def get_vpn(self, username: str):
        url = self.api_builder.vpn_detail_url(username=username)
        headers = self.get_auth_header()
        r = self.do_request(method='get', url=url, ok_status_codes=[200], headers=headers)
        return r.json()

    def create_vpn(self, username: str, password: str = None):
        data = {'username': username}
        if password:
            data['password'] = password

        url = self.api_builder.vpn_base_url()
        headers = self.get_auth_header()
        r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        return r.json()

    def get_vpn_or_create(self, username: str):
        url = self.api_builder.vpn_detail_url(username=username)
        headers = self.get_auth_header()
        r = self.do_request(method='get', url=url, ok_status_codes=[200, 404], headers=headers)
        d = r.json()
        if r.status_code == 200:
            return d

        if 'err_code' in d and d['err_code'] == 'NoSuchVPN':
            return self.create_vpn(username=username)

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

    def vpn_change_password(self, username: str, password: str):
        url = self.api_builder.vpn_detail_url(username=username, query={'password': password})
        headers = self.get_auth_header()
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
