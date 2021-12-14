from datetime import datetime, timedelta

from adapters import outputs, inputs
from adapters import exceptions
from adapters.params import ParamsName
from adapters.base import BaseAdapter
from .sdk.client import UnisCloud
from .sdk.auth import Credentials
from .sdk.model import RequestError


class UnisAdapter(BaseAdapter):
    adapter_name = 'Unis cloud adapter'

    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = '2020-07-30',
                 **kwargs
                 ):
        api_version = api_version.lower()
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth, **kwargs)
        self.region = self.kwargs.get(ParamsName.REGION, '')

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs) -> outputs.AuthenticateOutput:
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()
        """
        region = self.region
        credentials = Credentials(access_key=params.username, secret_key=params.password)
        unis = UnisCloud(
            credentials=credentials,
            endpoint_url=self.endpoint_url,
            region_id=region,
            version=self.api_version
        )
        try:
            r = unis.list_user_region()
        except RequestError as e:
            raise exceptions.AuthenticationFailed(message=str(e))

        if r.status_code == 401:
            raise exceptions.AuthenticationFailed(message=f'access_key_id or secret_key invalid,{r.text}')

        if r.status_code != 200:
            raise exceptions.AuthenticationFailed(message=r.text)
        data = r.json()
        expire = (datetime.utcnow() + timedelta(hours=2)).timestamp()
        auth = outputs.AuthenticateOutput(style='key', token='', header=None, query=None,
                                          expire=int(expire), access_key=params.username, secret_key=params.password)
        self.auth = auth
        return auth

    def get_unis_client(self, region: str):
        credentials = Credentials(access_key=self.auth.access_key, secret_key=self.auth.secret_key)
        return UnisCloud(
            credentials=credentials,
            endpoint_url=self.endpoint_url,
            region_id=region,
            version=self.api_version
        )

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        raise NotImplementedError('`server_create()` must be implemented.')

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        unis = self.get_unis_client(region=self.region)
        try:
            try:
                status = self._get_server_status(instance_id=params.server_id)
            except exceptions.Error as e:
                return outputs.ServerDeleteOutput(ok=False, error=e)

            if status not in ['DOWN', 'DISABLED', 'MISS']:
                return outputs.ServerDeleteOutput(
                    ok=False, error=exceptions.Error(f'云主机需要处于已停止/已停服状态才允许删除'))

            self.server_status(inputs.ServerStatusInput(server_id=params.server_id))
            r = unis.compute.delete_server(instance_id=params.server_id)
            if r.status_code == 200:
                try:
                    status = self._get_server_status(instance_id=params.server_id)
                except exceptions.Error as e:
                    return outputs.ServerDeleteOutput(ok=False, error=e)

                if status == 'MISS':
                    return outputs.ServerDeleteOutput()

            try:
                data = r.json()
                msg = data['Message']
            except Exception as e:
                msg = r.text

            return outputs.ServerDeleteOutput(
                ok=False, error=exceptions.Error(f'delete server failed, {msg}'))
        except Exception as e:
            message = f'delete server failed, {str(e)}'
            return outputs.ServerDeleteOutput(ok=False, error=exceptions.Error(message))

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        instance_id = params.server_id
        action = params.action
        unis = self.get_unis_client(region=self.region)
        try:
            if action == inputs.ServerAction.START:
                r = unis.compute.start_server(instance_id=instance_id)
            elif action == inputs.ServerAction.SHUTDOWN:
                r = unis.compute.stop_server(instance_id=instance_id)
            elif action in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
                ret = self.server_delete(params=inputs.ServerDeleteInput(server_id=instance_id))
                return outputs.ServerActionOutput(ok=ret.ok, error=ret.error)
            elif action == inputs.ServerAction.POWER_OFF:
                r = unis.compute.stop_server(instance_id=instance_id)
            elif action == inputs.ServerAction.REBOOT:
                r = unis.compute.reboot_server(instance_id=instance_id)
            else:
                return outputs.ServerActionOutput(
                    ok=False, error=exceptions.Error(f'server action failed, unknown action "{action}"'))

            if r.status_code == 200:
                return outputs.ServerActionOutput()

            msg = self._get_response_failed_message(r)
            return outputs.ServerActionOutput(
                ok=False, error=exceptions.Error(f'server action failed, {msg}'))
        except Exception as e:
            message = f'server action failed, {str(e)}'
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error(message))

    def _get_server_status(self, instance_id: str):
        """
        get unis instance status string

        :return:
            code: str       # success get
            "MISS"          # miss
            None            # unknown status

        :raises: Error
        """
        unis = self.get_unis_client(region=self.region)
        try:
            r = unis.compute.detail_server(instance_id=instance_id)
            if r.status_code == 200:
                data = r.json()
                if 'status' not in data:
                    if 'id' in data:
                        return None
                    else:
                        return 'MISS'
                else:
                    status = data['status']
                    status = status.upper()
                    return status

            msg = self._get_response_failed_message(r)
            raise exceptions.Error(message=f'get server status failed, {msg}', status_code=r.status_code)
        except Exception as e:
            raise exceptions.Error(message=str(e))

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        status_map = {
            'RUNNING': outputs.ServerStatus.RUNNING,
            'CREATING': outputs.ServerStatus.BUILDING,
            'SHUTTING_DOWN': outputs.ServerStatus.SHUTDOWN,
            'DOWN': outputs.ServerStatus.SHUTOFF,
            'BOOTING': outputs.ServerStatus.RUNNING,
            'REBOOTING': outputs.ServerStatus.RUNNING,
            'REBUILDING': outputs.ServerStatus.REBUILDING,
            'STOPPING': outputs.ServerStatus.PAUSED,
            'DISABLED': outputs.ServerStatus.BLOCKED,
            'ERROR': outputs.ServerStatus.ERROR,
            'UPGRADING': outputs.ServerStatus.NOSTATE,
            'RESUMING': outputs.ServerStatus.NOSTATE,
            'CREATING_SYS_SNAPSHOT': outputs.ServerStatus.NOSTATE,
            'SYS_ROLLING_BACK': outputs.ServerStatus.NOSTATE,
        }

        try:
            status = self._get_server_status(instance_id=params.server_id)
        except exceptions.Error as e:
            return outputs.ServerStatusOutput(
                ok=False, error=e, status=outputs.ServerStatus.NOSTATE, status_mean=''
            )

        if status == 'MISS':
            code = outputs.ServerStatus.MISS
        elif status in status_map:
            code = status_map[status]
        else:
            code = outputs.ServerStatus.NOSTATE

        status_mean = outputs.ServerStatus.get_mean(code)
        return outputs.ServerStatusOutput(status=code, status_mean=status_mean)

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        unis = self.get_unis_client(region=self.region)
        r = unis.compute.get_server_vnc(instance_id=params.server_id)
        if r.status_code != 200:
            return outputs.ListImageOutput(
                ok=False, error=exceptions.Error(message=r.text, status_code=r.status_code), images=[]
            )

        data = r.json()
        vnc = outputs.ServerVNCOutputVNC(
            url=data['wssAddress']
        )
        return outputs.ServerVNCOutput(vnc=vnc)

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        unis = self.get_unis_client(region=self.region)
        r = unis.compute.detail_server(instance_id=params.server_id)
        if r.status_code != 200:
            return outputs.ListImageOutput(
                ok=False, error=exceptions.Error(message=r.text, status_code=r.status_code), images=[]
            )

        data = r.json()
        password = ''
        try:
            r = unis.compute.get_server_password(instance_id=params.server_id)
            if r.status_code == 200:
                password = r.json()['password']
        except Exception as e:
            pass

        image = outputs.ServerImage(
            _id=data['imageId'],
            name='',
            system='',
            desc=''
        )
        r = self.list_images(inputs.ListImageInput(region_id=self.region))
        if r.ok:
            for img in r.images:
                if img.id == data['imageId']:
                    image.name = img.name
                    image.system = img.system
                    break

        eip = data['eipIp']
        if eip:
            ip = outputs.ServerIP(
                ipv4=eip,
                public_ipv4=True
            )
        else:
            ip = outputs.ServerIP(
                ipv4=data['ip'],
                public_ipv4=False
            )

        server = outputs.ServerDetailOutputServer(
            uuid=data['id'],
            ram=data['memory'] * 1024,
            vcpu=data['cpu'],
            image=image,
            ip=ip,
            creation_time=datetime.fromtimestamp(data['startTime'] / 1000),
            default_user='root',
            default_password=password
        )

        return outputs.ServerDetailOutput(server=server)

    def server_rebuild(self, params: inputs.ServerRebuildInput, **kwargs):
        """
        重建（更换系统镜像）虚拟服务器
        :return:
            outputs.ServerRebuildOutput()
        """
        raise NotImplementedError('`server_rebuild()` must be implemented.')

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        images = []
        unis = self.get_unis_client(region=params.region_id)
        r = unis.compute.list_images()
        if r.status_code != 200:
            return outputs.ListImageOutput(
                ok=False, error=exceptions.Error(message=r.text, status_code=r.status_code), images=[]
            )

        data = r.json()
        unis_images = data['images']
        for img in unis_images:
            image = outputs.ListImageOutputImage(
                _id=img['imageId'],
                name=img['operatingSystem'],
                system=img['operatingSystem'],
                system_type=img['ostype'],
                creation_time=datetime.fromtimestamp(img['creationTime'] / 1000),
                default_username='root',
                default_password=''
            )
            images.append(image)

        return outputs.ListImageOutput(images=images)

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
            outputs.ListNetworkOutput()
        """
        raise NotImplementedError('`list_networks()` must be implemented.')

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        raise NotImplementedError('`network_detail()` must be implemented.')

    def _get_response_failed_message(self, response):
        try:
            data = response.json()
            msg = data['Message']
        except Exception as e:
            msg = response.text

        return msg
