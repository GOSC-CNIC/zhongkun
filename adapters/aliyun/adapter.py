import uuid
from datetime import datetime, timedelta
from urllib3.util.url import parse_url
import string
import random

from alibabacloud_ecs20140526.client import Client as Ecs20140526Client
from alibabacloud_ecs20140526 import models as ecs_20140526_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_vpc20160428 import models as vpc_20160428_models

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
from adapters import exceptions
from adapters.aliyun import helpers


class AliyunAdapter(BaseAdapter):
    """
    Vmware服务API适配器
    """

    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = 'v3',
                 region: str = None,
                 ):
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth)
        self.url = parse_url(self.endpoint_url)
        self.region = region

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs):
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()

        :raises: AuthenticationFailed, Error
        """
        username = params.username
        password = params.password

        try:
            """
                   使用AK&SK初始化账号Client
                   @param access_key_id:
                   @param access_key_secret:
                   @return: Client
                   @throws Exception
                   """
            config = open_api_models.Config(
                # 必填，您的 AccessKey ID,
                access_key_id=username,
                # 必填，您的 AccessKey Secret,
                access_key_secret=password
            )
            # 访问的域名
            config.endpoint = self.url.netloc

            service_instance = Ecs20140526Client(config)
            expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()
            auth = outputs.AuthenticateOutput(style='token', token='', header=None, query=None,
                                              expire=int(expire), username=username, password=password,
                                              vmconnect=service_instance)
        except Exception as e:
            raise exceptions.AuthenticationFailed(message=str(e))

        self.auth = auth
        return auth

    def _get_connect(self):
        return self.auth.kwargs['vmconnect']

    @staticmethod
    def _build_instance_name(template_name: str):
        return f'uuid_{str(uuid.uuid1())}'

    @staticmethod
    def _get_template_name(server_name: str):
        if '&' not in server_name:
            return ''

        template_name, _uuid = server_name.split('&', maxsplit=1)
        try:
            uuid.UUID(_uuid)
        except ValueError as e:
            return ''

        return template_name

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        try:

            aliyun_instance_type = params.flavor_id
            if not aliyun_instance_type:
                return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('阿里云适配器：缺少服务端规格ID参数（flavor_id)'),
                                                  server=None)
            vm_name = self._build_instance_name(params.image_id)

            security_group_id = None

            conn = self._get_connect()
            runtime = util_models.RuntimeOptions()

            describe_security_groups_request = ecs_20140526_models.DescribeSecurityGroupsRequest(
                region_id=params.region_id
            )

            response = conn.describe_security_groups_with_options(describe_security_groups_request, runtime)
            for group in response.body.security_groups.security_group:
                security_group_id = group.security_group_id

            # describe_available_resource_request = ecs_20140526_models.DescribeAvailableResourceRequest(
            #     region_id=params.region_id,
            #     instance_charge_type='PostPaid',
            #     zone_id=params.azone_id,
            #     cores=params.vcpu,
            #     memory=params.ram / 1024,
            #     destination_resource='InstanceType'
            # )
            #
            # response = conn.describe_available_resource_with_options(describe_available_resource_request, runtime)
            # for zone in response.body.available_zones.available_zone:
            #     for resource in zone.available_resources.available_resource:
            #         for support_res in resource.supported_resources.supported_resource:
            #             aliyun_instance_type = support_res.value
            #             break
            #         break
            #     break
            # if not aliyun_instance_type:
            #     return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('该区不支持选择的资源配置'), server=None)

            system_disk = ecs_20140526_models.RunInstancesRequestSystemDisk(
                size=str(params.systemdisk_size)
            )
            os_default_password = "".join(random.sample(string.ascii_uppercase, 2)) + "".join(
                random.sample(string.ascii_lowercase, 2)) + "".join(random.sample(string.digits, 2)) + "".join(
                random.sample(string.punctuation, 2))
            run_instances_request = ecs_20140526_models.RunInstancesRequest(
                region_id=params.region_id,
                image_id=params.image_id,
                instance_name=vm_name,
                instance_type=aliyun_instance_type,
                security_group_id=security_group_id,
                v_switch_id=params.network_id,
                password=os_default_password,
                system_disk=system_disk
            )
            response = conn.run_instances_with_options(run_instances_request, runtime)
            if response.status_code == 200:
                for vm_id in response.body.instance_id_sets.instance_id_set:
                    server = outputs.ServerCreateOutputServer(
                        uuid=vm_id, name=vm_name, default_user='root/administrator',
                        default_password=os_default_password
                    )
                    return outputs.ServerCreateOutput(server=server)
            return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('创建云主机失败'), server=None)
        except Exception as e:
            return outputs.ServerCreateOutput(ok=False, error=exceptions.Error(f'创建云主机失败:{str(e)}'), server=None)

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        try:
            conn = self._get_connect()

            describe_instances_request = ecs_20140526_models.DescribeInstancesRequest(
                region_id=self.region,
                instance_ids=f'["{params.instance_id}"]'
            )
            runtime = util_models.RuntimeOptions()
            response = conn.describe_instances_with_options(describe_instances_request, runtime)
            for vm in response.body.instances.instance:
                if len(vm.public_ip_address.ip_address) > 0:
                    ip = outputs.ServerIP(ipv4=vm.public_ip_address.ip_address[0], public_ipv4=True)
                elif len(vm.network_interfaces.network_interface) > 0:
                    ip = outputs.ServerIP(ipv4=vm.network_interfaces.network_interface[0].primary_ip_address,
                                          public_ipv4=False)
                else:
                    ip = outputs.ServerIP(ipv4='0.0.0.0', public_ipv4=False)

                image = outputs.ServerImage(
                    _id=vm.image_id,
                    name=vm.image_id,
                    system=vm.osname,
                    desc=''
                )
                server = outputs.ServerDetailOutputServer(
                    uuid=vm.instance_id,
                    name=vm.instance_name,
                    ram=vm.memory,
                    vcpu=vm.cpu,
                    ip=ip,
                    image=image,
                    creation_time=helpers.iso_to_datetime(vm.creation_time),
                    default_user='',
                    default_password='',
                    azone_id='',
                    disk_size=0
                )
                return outputs.ServerDetailOutput(server=server)
            return outputs.ServerDetailOutput(ok=False, error=exceptions.Error('查询不到ECS实例'), server=None)
        except Exception as e:
            return outputs.ServerDetailOutput(ok=False, error=exceptions.Error(str(e)), server=None)

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        try:
            service_instance = self._get_connect()
            runtime = util_models.RuntimeOptions()

            vm_detail = self.server_detail(inputs.ServerDetailInput(instance_id=params.instance_id),
                                           region_id=self.region)
            if not vm_detail.ok:
                return outputs.ServerActionOutput()
            delete_instance_request = ecs_20140526_models.DeleteInstanceRequest(
                instance_id=params.instance_id,
                force=True
            )
            response = service_instance.delete_instance_with_options(delete_instance_request, runtime)
            return outputs.ServerActionOutput()
        except Exception as e:
            msg = 'Failed to destroy server.'
            if hasattr(e, 'msg'):
                msg += e.msg
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error(msg))

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        try:
            service_instance = self._get_connect()
            runtime = util_models.RuntimeOptions()

            vm_detail = self.server_detail(inputs.ServerDetailInput(instance_id=params.instance_id),
                                           region_id=self.region)
            if not vm_detail.ok:
                return outputs.ServerActionOutput()
            if params.action == inputs.ServerAction.START:
                start_instance_request = ecs_20140526_models.StartInstanceRequest(
                    instance_id=params.instance_id
                )
                response = service_instance.start_instance_with_options(start_instance_request, runtime)
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.SHUTDOWN:
                stop_instance_request = ecs_20140526_models.StopInstanceRequest(
                    instance_id=params.instance_id
                )
                response = service_instance.stop_instance_with_options(stop_instance_request, runtime)
                return outputs.ServerActionOutput()
            elif params.action in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
                delete_instance_request = ecs_20140526_models.DeleteInstanceRequest(
                    instance_id=params.instance_id,
                    force=True
                )
                response = service_instance.delete_instance_with_options(delete_instance_request, runtime)
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.POWER_OFF:
                stop_instance_request = ecs_20140526_models.StopInstanceRequest(
                    instance_id=params.instance_id,
                    force_stop=True
                )
                response = service_instance.stop_instance_with_options(stop_instance_request, runtime)
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.REBOOT:
                reboot_instance_request = ecs_20140526_models.RebootInstanceRequest(
                    instance_id=params.instance_id,
                )
                response = service_instance.reboot_instance_with_options(reboot_instance_request, runtime)
                return outputs.ServerActionOutput()
            else:
                return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))
        except Exception as e:
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error(f'server action failed:{str(e)}'))

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        status_map = {
            'Pending': outputs.ServerStatus.BUILDING,
            'Running': outputs.ServerStatus.RUNNING,
            'Starting': outputs.ServerStatus.RUNNING,
            'Stopping': outputs.ServerStatus.SHUTOFF,
            'Stopped': outputs.ServerStatus.SHUTOFF,
        }
        try:
            service_instance = self._get_connect()

            describe_instance_status_request = ecs_20140526_models.DescribeInstanceStatusRequest(
                region_id=self.region,
                instance_id=[
                    params.instance_id
                ]
            )
            runtime = util_models.RuntimeOptions()
            vm = service_instance.describe_instance_status_with_options(describe_instance_status_request, runtime)
            if len(vm.body.instance_statuses.instance_status) < 1:
                return outputs.ServerStatusOutput(status=outputs.ServerStatus.MISS,
                                                  status_mean=outputs.ServerStatus.get_mean(outputs.ServerStatus.MISS))

            state = vm.body.instance_statuses.instance_status[0].status
            if state not in status_map:
                state = 'unknown'

            status_code = status_map[state]
            status_mean = outputs.ServerStatus.get_mean(status_code)
            return outputs.ServerStatusOutput(status=status_code, status_mean=status_mean)
        except Exception as e:
            return outputs.ServerStatusOutput(ok=False, error=exceptions.Error(f'get server status failed:{str(e)}'),
                                              status=outputs.ServerStatus.NOSTATE, status_mean='')

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        try:
            is_windows = False
            service_instance = self._get_connect()
            runtime = util_models.RuntimeOptions()
            describe_instances_request = ecs_20140526_models.DescribeInstancesRequest(
                region_id=self.region,
                instance_ids=f'["{params.instance_id}"]'
            )
            response = service_instance.describe_instances_with_options(describe_instances_request, runtime)
            for vm in response.body.instances.instance:
                if vm.ostype == 'windows':
                    is_windows = True
                else:
                    is_windows = False
                break

            vnc_password = "".join(random.sample(string.ascii_uppercase, 2)) + "".join(
                random.sample(string.ascii_lowercase, 2)) + "".join(random.sample(string.digits, 2))
            modify_instance_vnc_passwd_request = ecs_20140526_models.ModifyInstanceVncPasswdRequest(
                instance_id=params.instance_id,
                region_id=self.region,
                vnc_password=vnc_password
            )
            service_instance.modify_instance_vnc_passwd_with_options(modify_instance_vnc_passwd_request, runtime)
            describe_instance_vnc_url_request = ecs_20140526_models.DescribeInstanceVncUrlRequest(
                instance_id=params.instance_id,
                region_id=self.region
            )
            reponse = service_instance.describe_instance_vnc_url_with_options(describe_instance_vnc_url_request,
                                                                              runtime)
            vnc_url = f'https://g.alicdn.com/aliyun/ecs-console-vnc2/0.0.8/index.html?vncUrl={reponse.body.vnc_url}&instanceId={params.instance_id}&isWindows={str(is_windows)}&password={vnc_password}'
            return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=vnc_url))
        except Exception as e:
            return outputs.ServerVNCOutput(ok=False, error=exceptions.Error(f'get vnc failed:{str(e)}'), vnc=None)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        try:
            if params.page_size > 100:
                return outputs.ListImageOutput(ok=False, error=exceptions.Error(f'阿里云适配器，pagesize不能大于100'),
                                               images=[])
            service_instance = self._get_connect()
            if not params.flavor_id or params.flavor_id == '':
                return outputs.ServerCreateOutput(ok=False, error=exceptions.Error('阿里云适配器：缺少服务端规格ID参数（flavor_id)'),
                                                  server=None)
            else:
                describe_images_request = ecs_20140526_models.DescribeImagesRequest(region_id=params.region_id,
                                                                                    page_size=params.page_size,
                                                                                    instance_type=params.flavor_id,
                                                                                    page_number=params.page_num)
            runtime = util_models.RuntimeOptions()
            response = service_instance.describe_images_with_options(describe_images_request, runtime)
            result = []
            for image_aliyun in response.body.images.image:
                img_obj = outputs.ListImageOutputImage(
                    _id=image_aliyun.image_id, name=image_aliyun.osname,
                    release=image_aliyun.platform,
                    version="Unknown",
                    architecture=image_aliyun.architecture,
                    desc=image_aliyun.description,
                    system_type=image_aliyun.ostype,
                    creation_time=image_aliyun.creation_time,
                    default_username='none', default_password='none',
                    min_sys_disk_gb=image_aliyun.size, min_ram_mb=0
                )
                result.append(img_obj)
            return outputs.ListImageOutput(images=result, count=response.body.total_count)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error(f'list image failed, {str(e)}'), images=[])

    def image_detail(self, params: inputs.ImageDetailInput, **kwargs):
        """
        查询镜像信息
        :return:
            output.ImageDetailOutput()
        """
        image_id = params.image_id
        region_id = 'cn-hangzhou'
        if params.region_id:
            region_id = params.region_id
        service_instance = self._get_connect()
        describe_images_request = ecs_20140526_models.DescribeImagesRequest(region_id=region_id, image_id=image_id)
        runtime = util_models.RuntimeOptions()
        response = service_instance.describe_images_with_options(describe_images_request, runtime)
        for image_aliyun in response.body.images.image:
            img_obj = outputs.ListImageOutputImage(
                _id=image_aliyun.image_id, name=image_aliyun.osname,
                release=image_aliyun.platform,
                version="Unknown",
                architecture=image_aliyun.architecture,
                desc=image_aliyun.description,
                system_type=image_aliyun.ostype,
                creation_time=image_aliyun.creation_time,
                default_username='none', default_password='noe',
                min_sys_disk_gb=image_aliyun.size, min_ram_mb=0
            )
            return outputs.ImageDetailOutput(image=img_obj)

        return outputs.ImageDetailOutput(ok=False, error=exceptions.ResourceNotFound(), image=None)

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        try:
            service_instance = self._get_connect()
            describe_vswitches_request = vpc_20160428_models.DescribeVSwitchesRequest(
                region_id=params.region_id,
                zone_id=params.azone_id
            )
            runtime = util_models.RuntimeOptions()
            networks_response = service_instance.describe_vswitches_with_options(describe_vswitches_request, runtime)
            result = []
            for switch in networks_response.body.v_switches.v_switch:
                public = False
                new_net = outputs.ListNetworkOutputNetwork(_id=switch.v_switch_id, name=switch.v_switch_name,
                                                           public=public,
                                                           segment=switch.cidr_block)
                result.append(new_net)
            return outputs.ListNetworkOutput(networks=result)

        except Exception as e:
            return outputs.ListNetworkOutput(
                ok=False, error=exceptions.Error(f'list networks failed, {str(e)}'), networks=[])

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        try:
            service_instance = self._get_connect()
            describe_vswitches_request = vpc_20160428_models.DescribeVSwitchesRequest(
                region_id=self.region,
                zone_id=params.azone_id,
                v_switch_id=params.network_id
            )
            runtime = util_models.RuntimeOptions()
            networks_response = service_instance.describe_vswitches_with_options(describe_vswitches_request, runtime)
            for switch in networks_response.body.v_switches.v_switch:
                public = False
                new_net = outputs.ListNetworkOutputNetwork(_id=switch.v_switch_id, name=switch.v_switch_name,
                                                           public=public,
                                                           segment=switch.cidr_block)
                return outputs.NetworkDetailOutput(network=new_net)

            return outputs.NetworkDetailOutput(ok=False, error=exceptions.ResourceNotFound(), network=None)
        except exceptions.Error as e:
            return outputs.NetworkDetailOutput(ok=False, error=exceptions.Error(str(e)), network=None)

    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput):
        try:
            zones = []
            service_instance = self._get_connect()

            describe_zones_request = ecs_20140526_models.DescribeZonesRequest(
                region_id=self.region
            )
            runtime = util_models.RuntimeOptions()
            zones_response = service_instance.describe_zones_with_options(describe_zones_request, runtime)
            for zone in zones_response.body.zones.zone:
                zones.append(outputs.AvailabilityZone(_id=str(zone.zone_id), name=zone.local_name))
            return outputs.ListAvailabilityZoneOutput(zones)
        except Exception as e:
            return outputs.ListAvailabilityZoneOutput(ok=False, error=exceptions.Error(str(e)), zones=None)
