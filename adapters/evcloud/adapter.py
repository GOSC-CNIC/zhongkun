from datetime import datetime
import requests

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
from adapters.params import GenericAdapterParams
from .builders import APIBuilder
from . import exceptions
from .validators import InputValidator
from .converters import OutputConverter


def get_failed_msg(response, msg_key='code_text'):
    """
    请求失败错误信息

    :param response: requests.Response()
    :param msg_key: 信息键值
    :return:
    """
    try:
        data = response.json()
        msg = data.get(msg_key, '')
        return msg
    except Exception:
        return ''


def get_failed_err_code(response, code_key='err_code'):
    """
    请求失败错误码

    :param response: requests.Response()
    :param code_key: 信息键值
    :return:
    """
    try:
        data = response.json()
        code = data.get(code_key, '')
        return code
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
                 api_version: str = 'v3',
                 **kwargs
                 ):
        api_version = api_version.lower()
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth, **kwargs)
        self.api_builder = APIBuilder(endpoint_url=self.endpoint_url, api_version=self.api_version)

    def get_region(self):
        return self.kwargs.get(GenericAdapterParams.REGION, '')

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
            params = inputs.AuthenticateInput(username=auth.username, password=auth.password)
            auth = self.authenticate(params=params)

        if not auth.ok:
            if isinstance(auth.error, exceptions.Error):
                raise auth.error

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
        err_code = get_failed_err_code(r)
        raise exceptions.APIError(msg, status_code=r.status_code, err_code=err_code)

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs) -> outputs.AuthenticateOutput:
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()
        """
        try:
            auth = self.authenticate_jwt(username=params.username, password=params.password)
        except exceptions.Error:
            auth = self.authenticate_token(username=params.username, password=params.password)

        self.auth = auth
        return auth

    def authenticate_jwt(self, username, password):
        url = self.api_builder.jwt_base_url()
        try:
            r = requests.post(url, data={'username': username, 'password': password}, timeout=(6, 60))
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
            r = requests.post(url, data={'username': username, 'password': password}, timeout=(6, 60))
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
            if params.systemdisk_size:
                if params.systemdisk_size < self.SYSTEM_DISK_MIN_SIZE_GB:
                    return outputs.ServerCreateOutput(
                        ok=False, error=exceptions.Error(message=f'系统盘大小不能小于{self.SYSTEM_DISK_MIN_SIZE_GB} GiB'),
                        server=None
                    )
            else:
                params.systemdisk_size = None

            data = InputValidator.create_server_validate(params)
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=url, data=data, ok_status_codes=[201], headers=headers)
        except exceptions.Error as e:
            return OutputConverter.to_server_create_output_error(error=e)

        rj = r.json()
        return OutputConverter.to_server_create_output(rj['vm'])

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        query = None
        if params.force:
            query = {'force': 'true'}
        url = self.api_builder.vm_detail_url(vm_uuid=params.instance_id, query=query)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='delete', url=url, ok_status_codes=[204, 400, 404], headers=headers)
        except exceptions.Error as e:
            return outputs.ServerDeleteOutput(ok=False, error=e)

        if r.status_code == 204:
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
            params = inputs.ServerDeleteInput(instance_id=params.instance_id, instance_name=params.instance_name)
            if action == inputs.ServerAction.DELETE_FORCE:
                params.force = True
            r = self.server_delete(params=params)
            if r.ok:
                return outputs.ServerActionOutput()

            return outputs.ServerActionOutput(ok=False, error=r.error)

        try:
            url = self.api_builder.vm_action_url(vm_uuid=params.instance_id)
            headers = self.get_auth_header()
            self.do_request(method='patch', url=url, data={'op': action}, headers=headers)
        except exceptions.Error as e:
            return outputs.ServerActionOutput(ok=False, error=e)

        return outputs.ServerActionOutput()

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        url = self.api_builder.vm_status_url(vm_uuid=params.instance_id)
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
        url = self.api_builder.vm_vnc_url(vm_uuid=params.instance_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_server_vnc_output_error(error=e)

        rj = r.json()
        return OutputConverter().to_server_vnc_output(url=rj['vnc']['url'])

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        url = self.api_builder.vm_detail_url(vm_uuid=params.instance_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', ok_status_codes=[200, 404], url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_server_detail_output_error(error=e)

        rj = r.json()
        if r.status_code == 200:
            return OutputConverter().to_server_detail_output(vm=rj['vm'])

        if rj.get('err_code') == 'VmNotExist':
            err = exceptions.ServerNotExistError(status_code=404)
        else:
            msg = get_failed_msg(r)
            err = exceptions.APIError(message=msg, status_code=r.status_code)
        return OutputConverter().to_server_detail_output_error(error=err)

    def server_rebuild(self, params: inputs.ServerRebuildInput, **kwargs):
        """
        重建（更换系统镜像）虚拟服务器
        :return:
            outputs.ServerRebuildOutput()
        """
        url = self.api_builder.vm_reset_url(vm_uuid=params.instance_id, image_id=params.image_id)
        try:
            headers = self.get_auth_header()
            self.server_action(params=inputs.ServerActionInput(
                instance_id=params.instance_id, action=inputs.ServerAction.POWER_OFF))
            r = self.do_request(method='post', ok_status_codes=[200, 201, 404], url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_server_rebuild_output_error(error=e)

        if r.status_code == 201:
            rj = r.json()
            instance_id = params.instance_id
            image_id = params.image_id
            default_user = ''
            default_password = ''
            if 'vm' in rj and isinstance(rj['vm'], dict):
                vm = rj['vm']
                default_user = vm.get('default_user', '')
                default_password = vm.get('default_password', '')
            return OutputConverter().to_server_rebuild_output(
                server_id=instance_id, image_id=image_id, default_user=default_user, default_password=default_password
            )

        rj = r.json()
        if rj.get('err_code') == 'VmNotExist':
            err = exceptions.ServerNotExistError(status_code=404)
        else:
            msg = get_failed_msg(r)
            err = exceptions.APIError(message=msg, status_code=r.status_code)
        return OutputConverter().to_server_detail_output_error(error=err)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            outputs.ListImageOutput()
        """
        center_id = int(params.region_id)
        offset = (int(params.page_num) - 1) * int(params.page_size)
        limit = params.page_size
        url = self.api_builder.image_base_url(
            query={'center_id': center_id, 'offset': offset, 'limit': limit})
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_list_image_output_error(error=e)
        rj = r.json()
        return OutputConverter().to_list_image_output(rj['results'], rj['count'])

    def image_detail(self, params: inputs.ImageDetailInput, **kwargs):
        """
        查询镜像信息
        :return:
            output.ImageDetailOutput()
        """
        try:
            image_id = int(params.image_id)
        except ValueError:
            return OutputConverter().to_image_detail_output_error(
                error=exceptions.ResourceNotFound()
            )

        url = self.api_builder.image_detail_url(image_id=image_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_image_detail_output_error(error=e)
        rj = r.json()
        return OutputConverter().to_image_detail_output(rj)

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:    outputs.ListNetworkOutput()
        """
        try:
            center_id = int(params.region_id)
        except ValueError:
            return OutputConverter().to_list_network_output_error(
                exceptions.APIInvalidParam(message='参数region_id无效'))

        query = {'center_id': center_id, 'available': 'true'}
        if params.azone_id:
            try:
                group_id = int(params.azone_id)
                query['group_id'] = group_id
            except ValueError:
                return OutputConverter().to_list_network_output_error(
                    exceptions.APIInvalidParam(message='参数azone_id无效'))

        public = params.public
        if public is not None:
            query['public'] = str(public).lower()

        url = self.api_builder.vlan_base_url(query=query)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            return OutputConverter().to_list_network_output_error(error=e)

        rj = r.json()
        return OutputConverter().to_list_network_output(networks=rj['results'])

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        url = self.api_builder.vlan_detail_url(pk=params.network_id)

        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=url, headers=headers)
        except exceptions.Error as e:
            if e.status_code in [400, 404]:
                e = exceptions.ResourceNotFoundError()

            return OutputConverter().to_network_detail_output_error(error=e)

        rj = r.json()
        return OutputConverter().to_network_detail_output(net=rj)

    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput):
        if params.region_id:
            region_id = params.region_id
        else:
            region_id = self.get_region()

        if not region_id:
            return outputs.ListAvailabilityZoneOutput(
                ok=False, error=exceptions.Error(message='param "region_id" is required'), zones=None)

        try:
            headers = self.get_auth_header()
            data = self.list_groups(region_id=region_id, headers=headers)
            zones = []
            for group in data['results']:
                available = True
                ebl = group.get('enable', None)
                if ebl is not None:
                    available = bool(ebl)

                zones.append(outputs.AvailabilityZone(
                    _id=str(group['id']), name=group['name'], available=available))

            return outputs.ListAvailabilityZoneOutput(zones)
        except Exception as e:
            return outputs.ListAvailabilityZoneOutput(ok=False, error=exceptions.Error(str(e)), zones=None)

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

    def disk_create(self, params: inputs.DiskCreateInput) -> outputs.DiskCreateOutput:
        """
        创建云硬盘
        :return:
            outputs.DiskCreateOutput()
        """
        _api = self.api_builder.disk_base_url()
        try:
            data = InputValidator.create_disk_validate(params)
            headers = self.get_auth_header()
            r = self.do_request(method='post', url=_api, data=data, ok_status_codes=[201], headers=headers)
        except exceptions.Error as e:
            return OutputConverter.to_disk_create_output_error(error=e)

        rj = r.json()
        return OutputConverter.to_disk_create_output(rj['disk'])

    def disk_create_pretend(self, params: inputs.DiskCreateInput) -> outputs.DiskCreatePretendOutput:
        """
        检查是否满足云硬盘的创建条件，是否有足够资源、其他什么限制等等

        :return:
            outputs.DiskCreatePretendOutput()
        """
        ret = self._list_disk_storage_pools(region_id=params.region_id, azone_id=params.azone_id)
        if not ret.ok:
            return outputs.DiskCreatePretendOutput(
                ok=True, error=None, result=False, reason=f'查询云硬盘存储池失败，{str(ret.error)}')

        ds_pools = ret.pools
        ok = False
        for p in ds_pools:
            if not p.available:
                continue
            if p.free_capacity_gb >= params.size_gib and p.max_size_limit_gb >= params.size_gib:
                ok = True
                break

        if not ok:
            return outputs.DiskCreatePretendOutput(
                ok=True, error=None, result=False, reason='没有满足资源需求的云硬盘存储池')

        return outputs.DiskCreatePretendOutput(ok=True, error=None, result=True, reason='')

    def _list_disk_storage_pools(self, region_id: str, azone_id: str) -> outputs.ListDiskStoragePoolsOutput:
        r = self.list_availability_zones(params=inputs.ListAvailabilityZoneInput(
            region_id=region_id
        ))
        if not r.ok:
            return outputs.ListDiskStoragePoolsOutput(ok=False, error=r.error, pools=[])

        available_az_ids = []
        if r.zones:
            available_az_ids = [az.id for az in r.zones if az.available]

        if azone_id:
            query = {'group_id': azone_id}
        else:
            query = None

        _api = self.api_builder.disk_quota_base_url(query=query)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=_api, ok_status_codes=[200], headers=headers)
        except exceptions.Error as e:
            return outputs.ListDiskStoragePoolsOutput(ok=False, error=e, pools=[])

        rj = r.json()
        pools = []
        for quota in rj['results']:
            _group = quota['group']
            if not (_group and str(_group['id']) in available_az_ids):
                continue

            total_capacity_gb = quota.get('total', 0)
            size_used = quota.get('size_used', 0)
            available = True
            # quota enable
            q_enable = quota.get('enable', None)
            if q_enable is False:
                available = False
            # quota pool enable
            if quota.get('pool', None):
                p_enable = quota['pool'].get('enable')
                if p_enable is False:
                    available = False

            p = outputs.DiskStoragePool(
                pool_id=quota['id'],
                name=quota.get('name', ''),
                total_capacity_gb=total_capacity_gb,
                free_capacity_gb=total_capacity_gb - size_used,
                max_size_limit_gb=quota.get('max_vdisk', 0),
                available=available
            )
            pools.append(p)

        return outputs.ListDiskStoragePoolsOutput(ok=True, pools=pools)

    def disk_detail(self, params: inputs.DiskDetailInput) -> outputs.DiskDetailOutput:
        """
        查询云硬盘
        :return:
            outputs.DiskDetailOutput()
        """
        _api = self.api_builder.disk_detail_url(disk_id=params.disk_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='get', url=_api, data=None, ok_status_codes=[200], headers=headers)
        except exceptions.Error as e:
            return OutputConverter.to_disk_detail_output_error(error=e)

        rj = r.json()
        data = rj.get('disk')   # 兼容以后接口响应disk内容键名可能由‘vm’更改为‘disk’
        if data and 'size' in data:
            pass
        else:
            data = rj['vm']     # 接口响应disk内容键名是‘vm’
        return OutputConverter.to_disk_detail_output(data=data, region_id=self.get_region())

    def disk_delete(self, params: inputs.DiskDeleteInput) -> outputs.DiskDeleteOutput:
        """
        删除云硬盘
        :return:
            outputs.DiskDeleteOutput()
        """
        _api = self.api_builder.disk_detail_url(disk_id=params.disk_id)
        try:
            headers = self.get_auth_header()
            r = self.do_request(method='delete', url=_api, data=None, ok_status_codes=[204, 404], headers=headers)
            if r.status_code == 204:
                return outputs.DiskDeleteOutput(ok=True)
            elif r.status_code == 404:
                err_code = get_failed_err_code(r)
                if err_code == 'VdiskNotExist':
                    return outputs.DiskDeleteOutput(ok=True)

            err_code = get_failed_err_code(r)
            msg = get_failed_msg(r)
            raise exceptions.APIError(msg, status_code=r.status_code, err_code=err_code)
        except exceptions.Error as e:
            return outputs.DiskDeleteOutput(ok=False, error=e)

    def disk_attach(self, params: inputs.DiskAttachInput) -> outputs.DiskAttachOutput:
        """
        云硬盘挂载到云主机
        :return:
            outputs.DiskAttachOutput()
        """
        _api = self.api_builder.disk_attach_url(disk_id=params.disk_id, vm_uuid=params.instance_id)
        try:
            headers = self.get_auth_header()
            self.do_request(method='patch', url=_api, data=None, ok_status_codes=[200], headers=headers)
        except exceptions.Error as e:
            return outputs.DiskAttachOutput(ok=False, error=e)

        return outputs.DiskAttachOutput(ok=True)

    def disk_detach(self, params: inputs.DiskDetachInput) -> outputs.DiskDetachOutput:
        """
        从云主机卸载云硬盘
        :return:
            outputs.DiskDetachOutput()
        """
        _api = self.api_builder.disk_detach_url(disk_id=params.disk_id)
        try:
            headers = self.get_auth_header()
            self.do_request(method='patch', url=_api, data=None, ok_status_codes=[200], headers=headers)
        except exceptions.Error as e:
            return outputs.DiskDetachOutput(ok=False, error=e)

        return outputs.DiskDetachOutput(ok=True)

    def get_vpn(self, username: str):
        url = self.api_builder.vpn_detail_url(username=username)
        headers = self.get_auth_header()
        r = self.do_request(method='get', url=url, ok_status_codes=[200, 404], headers=headers)
        if r.status_code == 200:
            return r.json()

        d = r.json()
        if 'err_code' in d and d['err_code'] == 'NoSuchVPN':
            raise exceptions.ResourceNotFound(message='vpn账号不存在', err_code=d['err_code'])

        msg = get_failed_msg(r)
        raise exceptions.APIError(msg, status_code=r.status_code)

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

    def vpn_active(self, username: str):
        url = self.api_builder.vpn_active_url(username=username)
        headers = self.get_auth_header()
        r = self.do_request(method='post', url=url, headers=headers)
        return r.json()

    def vpn_deactive(self, username: str):
        url = self.api_builder.vpn_deactive_url(username=username)
        headers = self.get_auth_header()
        r = self.do_request(method='post', url=url, headers=headers)
        return r.json()
