import string
import random
import uuid
from datetime import datetime, timedelta

from adapters import outputs, inputs
from adapters import exceptions
from adapters.params import ParamsName
from adapters.base import BaseAdapter
from .sdk import (
    UnisCloud, Credentials, RequestError
)
from . import sdk


def random_string(length: int = 8):
    letters = string.ascii_letters + string.digits
    items = [random.choice(letters) for _ in range(length)]
    return ''.join(items)


class UnisImagesContainer:
    PRIVATE = 'ecs.image.private'
    PUBLIC = 'ecs.image.public'

    def __init__(self):
        self._private = []
        self._public = []

    @property
    def private(self):
        return self._private

    @private.setter
    def private(self, val: list):
        self._private = val

    @property
    def public(self):
        return self._public

    @public.setter
    def public(self, val: list):
        self._public = val

    @property
    def all(self):
        return self._private + self.public

    def get_image(self, image_id: str) -> (str, dict):
        """
        :return:
            (               # exist
                str,        # 镜像规格族
                dict
            )
            None, None      # not exist

        """
        for img in self.private:
            if image_id == img['imageId']:
                return self.PRIVATE, img

        for img in self.public:
            if image_id == img['imageId']:
                return self.PUBLIC, img

        return None, None


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
        def return_exception(exc):
            return outputs.ServerCreateOutput(
                ok=False, error=exc, server=None
            )

        unis = self.get_unis_client(region=params.region_id)
        instance_name = f'gosc-{uuid.uuid1()}'

        # image
        try:
            images_container = self._list_images_unis(region_id=params.region_id)
        except exceptions.Error as exc:
            return return_exception(exc)
        except Exception as exc:
            return return_exception(exceptions.Error(message=str(exc), status_code=500))

        image_class_code, image = images_container.get_image(params.image_id)
        if image is None:
            return return_exception(exceptions.Error(message='image not found', status_code=404))

        system_type=image['ostype']
        default_password = random_string()
        default_username = 'root'
        if system_type == 'windows':
            default_username = 'Administrator'

        # network
        try:
            vpc_list = self._list_network_vpc(unis)
        except Exception as exc:
            return return_exception(exc)

        master_eni_subnet_id = params.network_id
        vpc_id = ''
        for vpc in vpc_list:
            for subnet in vpc['Subnets']:
                if subnet['Id'] == master_eni_subnet_id:
                    vpc_id = vpc['InstanceId']
                    break

        if not vpc_id:
            return return_exception(exceptions.Error(message='VPC subnet not found', status_code=404))

        # security group
        try:
            r = unis.network.security_group.list()
        except Exception as e:
            return return_exception(exceptions.Error(message=str(e), status_code=500))

        if r.status_code != 200:
            msg = self._get_response_failed_message(r)
            return return_exception(exceptions.Error(message=msg, status_code=r.status_code))

        security_group_id = ''
        data = r.json()
        security_groups = data['Res']['Data']
        if security_groups:
            for sg in data['Res']['Data']:
                if sg['Status'].upper() == 'RUNNING':
                    security_group_id = sg['InstanceId']
                    break

            if not security_group_id:
                return return_exception(exceptions.Error(message='not available security group', status_code=404))

        input = sdk.CreateInstanceInput(
            region_id=params.region_id,
            azone_id='zz',
            pay_type=sdk.CreateInstanceInput.PAY_TYPE_CHARGING_HOURS,
            period=1,
            vm_specification_code='vv',
            sys_disk_specification_code=sdk.CreateInstanceInput.SYS_DISK_CODE_SSD,
            sys_disk_size=40,
            image_id=params.image_id,
            image_specification_class_code=image_class_code,
            instance_name=instance_name,
            security_group_id=security_group_id,
            vpc_id=vpc_id,
            master_eni_subnet_id=master_eni_subnet_id,
            base_quantity=1,
            password=default_password,
            description=params.remarks
        )
        try:
            r = unis.compute.create_server(input=input)
        except Exception as exc:
            return return_exception(exceptions.Error(message=str(exc), status_code=500))

        if r.status_code != 200:
            msg = self._get_response_failed_message(r)
            return return_exception(exceptions.Error(message=msg, status_code=r.status_code))

        data = r.json()
        try:
            instance_id = data['instanceIds'][0]
        except IndexError:
            return return_exception(exceptions.Error(message='create instance failed', status_code=500))

        return outputs.ServerCreateOutput(
            server=outputs.ServerCreateOutputServer(
                uuid=instance_id,
                name=instance_name,
                default_user=default_username,
                default_password=default_password
            )
        )

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        unis = self.get_unis_client(region=self.region)
        try:
            try:
                status = self._get_server_status(instance_id=params.instance_id)
            except exceptions.Error as e:
                return outputs.ServerDeleteOutput(ok=False, error=e)

            if status not in ['DOWN', 'DISABLED', 'MISS']:
                return outputs.ServerDeleteOutput(
                    ok=False, error=exceptions.Error(f'云主机需要处于已停止/已停服状态才允许删除'))

            self.server_status(inputs.ServerStatusInput(instance_id=params.instance_id))
            r = unis.compute.delete_server(instance_id=params.instance_id)
            if r.status_code == 200:
                try:
                    status = self._get_server_status(instance_id=params.instance_id)
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
        instance_id = params.instance_id
        action = params.action
        unis = self.get_unis_client(region=self.region)
        try:
            if action == inputs.ServerAction.START:
                r = unis.compute.start_server(instance_id=instance_id)
            elif action == inputs.ServerAction.SHUTDOWN:
                r = unis.compute.stop_server(instance_id=instance_id)
            elif action in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
                ret = self.server_delete(params=inputs.ServerDeleteInput(instance_id=instance_id))
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
            status = self._get_server_status(instance_id=params.instance_id)
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
        r = unis.compute.get_server_vnc(instance_id=params.instance_id)
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
        r = unis.compute.detail_server(instance_id=params.instance_id)
        if r.status_code != 200:
            return outputs.ListImageOutput(
                ok=False, error=exceptions.Error(message=r.text, status_code=r.status_code), images=[]
            )

        data = r.json()
        password = ''
        try:
            r = unis.compute.get_server_password(instance_id=params.instance_id)
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
            name=data['name'],
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

    def _list_images_unis(self, region_id) -> UnisImagesContainer:
        """
        :raises: Error
        """
        unis = self.get_unis_client(region=region_id)
        r = unis.compute.list_private_images()
        if r.status_code != 200:
            msg = self._get_response_failed_message(r)
            raise exceptions.Error(message=msg, status_code=r.status_code)

        data = r.json()
        container = UnisImagesContainer()
        container.private = data['images']
        return container

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        try:
            images_container = self._list_images_unis(region_id=params.region_id)
        except exceptions.Error as exc:
            return outputs.ListImageOutput(
                ok=False, error=exc, images=[]
            )
        except Exception as exc:
            return outputs.ListImageOutput(
                ok=False, error=exceptions.Error(message=str(exc), status_code=500), images=[]
            )

        unis_images = images_container.all
        images = []
        for img in unis_images:
            system_type=img['ostype']
            default_username = 'root'
            if system_type == 'windows':
                default_username = 'Administrator'

            image = outputs.ListImageOutputImage(
                _id=img['imageId'],
                name=img['operatingSystem'],
                system=img['operatingSystem'],
                system_type=img['ostype'],
                creation_time=datetime.fromtimestamp(img['creationTime'] / 1000),
                default_username=default_username,
                default_password=''
            )
            images.append(image)

        return outputs.ListImageOutput(images=images)

    def _list_network_vpc(self, client):
        """
        :raises: Error
        """
        try:
            r = client.network.vpc.list()
        except Exception as exc:
            raise exceptions.Error(message=str(exc), status_code=500)

        if r.status_code != 200:
            msg = self._get_response_failed_message(r)
            raise exceptions.Error(message=msg, status_code=r.status_code)

        data = r.json()
        if data['Code'] != 'Network.Success':
            msg = data['Msg']
            raise exceptions.Error(message=msg, status_code=r.status_code)

        vpc_list = []
        for vpc in data['Res']:
            if vpc['Status'].upper() == 'RUNNING':
                vpc_list.append(vpc)

        if len(vpc_list) == 0:
            raise exceptions.Error(message='no VPC', status_code=r.status_code)

        return vpc_list

    def _list_network_vpc_subnet(self, client, vpcs: list):
        """
        :return:
            [
                {                   # vpc
                    'subnets': []   # vpc subnets
                }
            ]
        :raises: Error
        """
        for vpc in vpcs:
            try:
                r = client.network.vpc.list_subnet(vpc_id=vpc['InstanceId'])
            except Exception as exc:
                raise exceptions.Error(message=str(exc), status_code=500)

            if r.status_code != 200:
                msg = self._get_response_failed_message(r, key='message')
                raise exceptions.Error(message=msg, status_code=r.status_code)

            data = r.json()
            if data['Code'] != 'Network.Success':
                msg = data['Msg']
                raise exceptions.Error(message=msg, status_code=r.status_code)

            vpc['subnets'] = data['Res']

        return vpcs

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
            outputs.ListNetworkOutput()
        """
        unis = self.get_unis_client(region=params.region_id)
        try:
            vpc_list = self._list_network_vpc(unis)
        except Exception as exc:
            return outputs.ListNetworkOutput(ok=False, error=exc, networks=[])

        # try:
        #     vpc_list = self._list_network_vpc_subnet(unis, vpcs=vpc_list)
        # except Exception as exc:
        #     return outputs.ListNetworkOutput(ok=False, error=exc, networks=[])

        networks = []
        for vpc in vpc_list:
            for subnet in vpc['Subnets']:
                networks.append(
                    outputs.ListNetworkOutputNetwork(
                        _id=subnet['Id'], name=subnet['Name'], public=False, segment=subnet['Cidr']
                    )
                )

        return outputs.ListNetworkOutput(networks=networks)

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        unis = self.get_unis_client(region=self.region)
        try:
            vpc_list = self._list_network_vpc(unis)
        except Exception as exc:
            return outputs.NetworkDetailOutput(ok=False, error=exc)

        # try:
        #     subnets = self._list_network_vpc_subnet(unis, vpcs=vpc_list)
        # except Exception as exc:
        #     return outputs.NetworkDetailOutput(ok=False, error=exc)
        for vpc in vpc_list:
            for subnet in vpc['Subnets']:
                if subnet['Id'] == params.network_id:
                    return outputs.NetworkDetailOutput(
                        network=outputs.NetworkDetail(
                            _id=subnet['Id'],
                            name=subnet['Name'],
                            public=False,
                            segment=subnet['Cidr']
                        )
                    )

        return outputs.NetworkDetailOutput(
            ok=False, error=exceptions.Error(message='Not found subnet', status_code=404))

    def _get_response_failed_message(self, response, key: str = 'Message'):
        try:
            data = response.json()
            msg = data[key]
        except Exception as e:
            msg = response.text

        return msg
