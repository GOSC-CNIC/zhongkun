import uuid
from datetime import datetime, timedelta
from urllib3.util.url import parse_url

import atexit
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from pyVim.task import WaitForTask

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs
from adapters import exceptions
from . import helpers


class VmwareAdapter(BaseAdapter):
    """
    Vmware服务API适配器
    """

    def __init__(self,
                 endpoint_url: str,
                 auth: outputs.AuthenticateOutput = None,
                 api_version: str = 'v3'
                 ):
        api_version = api_version if api_version in ['v3'] else 'v3'
        super().__init__(endpoint_url=endpoint_url, api_version=api_version, auth=auth)
        self.url = parse_url(self.endpoint_url)

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs):
        """
        认证获取 Token

        :return:
            outputs.AuthenticateOutput()

        :raises: AuthenticationFailed, Error
        """
        username = params.username
        password = params.password
        port = 443
        if self.url.port:
            port = self.url.port
        elif self.url.scheme == 'https':
            port = 443
        else:
            port = 80

        try:
            service_instance = SmartConnectNoSSL(protocol=self.url.scheme,
                                                 host=self.url.host,
                                                 port=port,
                                                 user=username,
                                                 pwd=password
                                                 )
            atexit.register(Disconnect, service_instance)
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
        return f'{template_name}&{str(uuid.uuid1())}'

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

    @staticmethod
    def _get_instance(conn, instance_id: str, instance_name: str):
        vm = None
        if instance_id:
            vm = helpers.get_obj_by_uuid(conn.content, instance_id)

        if instance_name:
            if vm is not None:
                if vm.name.lower() != instance_name.lower():
                    vm = None
            else:
                vm = helpers.get_obj(conn.content, [vim.VirtualMachine], instance_name)

        return vm

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        template_name = params.image_id
        try:
            vm_name = self._build_instance_name(template_name)
            deploy_settings = {'cpus': params.vcpu, 'mem': params.ram, "new_vm_name": vm_name,
                               'template_name': template_name}

            # connect to vCenter server
            service_instance = self._get_connect()

            # add a clean up routine
            atexit.register(Disconnect, service_instance)
            content = service_instance.RetrieveContent()
            datacenter = helpers.get_obj(content, [vim.Datacenter], 'Datacenter')
            destfolder = datacenter.vmFolder
            cluster = helpers.get_obj(content, [vim.ClusterComputeResource], 'gosc-cluster')
            resource_pool = cluster.resourcePool  # use same root resource pool that my desired cluster uses
            datastore = helpers.get_obj(content, [vim.Datastore], 'datastore1')
            template_vm = helpers.get_obj(content, [vim.VirtualMachine], deploy_settings["template_name"])
            # Relocation spec
            relospec = vim.vm.RelocateSpec()
            relospec.datastore = datastore
            relospec.pool = resource_pool

            '''
             Networking config for VM and guest OS
            '''
            devices_changes = []

            for device in template_vm.config.hardware.device:
                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                    remove_nicspec = vim.vm.device.VirtualDeviceSpec()
                    remove_nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.remove
                    remove_nicspec.device = device
                    devices_changes.append(remove_nicspec)
            nic = vim.vm.device.VirtualDeviceSpec()
            nic.operation = vim.vm.device.VirtualDeviceSpec.Operation.add  # or edit if a device exists
            nic.device = vim.vm.device.VirtualVmxnet3()
            nic.device.wakeOnLanEnabled = True
            nic.device.addressType = 'assigned'
            nic.device.key = 4000  # 4000 seems to be the value to use for a vmxnet3 device
            nic.device.deviceInfo = vim.Description()
            nic.device.deviceInfo.label = "Network Adapter 22"
            nic.device.deviceInfo.summary = params.network_id
            nic.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            nic.device.backing.network = helpers.get_obj(content, [vim.Network], params.network_id)
            nic.device.backing.deviceName = params.network_id
            nic.device.backing.useAutoDetect = False
            nic.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nic.device.connectable.startConnected = True
            nic.device.connectable.allowGuestControl = True
            devices_changes.append(nic)

            # VM config spec
            vmconf = vim.vm.ConfigSpec()
            vmconf.numCPUs = deploy_settings['cpus']
            vmconf.memoryMB = deploy_settings['mem']
            vmconf.cpuHotAddEnabled = True
            vmconf.memoryHotAddEnabled = True
            vmconf.deviceChange = devices_changes

            # DNS settings
            globalip = vim.vm.customization.GlobalIPSettings()
            globalip.dnsServerList = ''
            globalip.dnsSuffixList = 'localhost'

            # Hostname settings
            ident = vim.vm.customization.LinuxPrep()
            ident.domain = 'localhost'
            ident.hostName = vim.vm.customization.FixedName()
            ident.hostName.name = deploy_settings["new_vm_name"]

            customspec = vim.vm.customization.Specification()
            customspec.identity = ident
            customspec.globalIPSettings = globalip

            # Clone spec
            clonespec = vim.vm.CloneSpec()
            clonespec.location = relospec
            clonespec.config = vmconf
            clonespec.customization = customspec
            clonespec.powerOn = True
            clonespec.template = False
            # fire the clone task
            task = template_vm.Clone(folder=destfolder, name=deploy_settings["new_vm_name"].title(), spec=clonespec)
            server = outputs.ServerCreateOutputServer(
                uuid='', name=vm_name, default_user='', default_password=''
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
            conn = self._get_connect()
            vm = self._get_instance(conn=conn, instance_id=params.instance_id, instance_name=params.instance_name)
            try:
                server_ip = {'ipv4': vm.guest.ipAddress, 'public_ipv4': None}
            except Exception as e:
                server_ip = {'ipv4': None, 'public_ipv4': None}

            ip = outputs.ServerIP(**server_ip)

            image_name = self._get_template_name(params.instance_name)
            if not image_name:
                image_name = helpers.get_system_name(vm)

            system = helpers.get_system_name(vm)
            image = outputs.ServerImage(
                _id='',
                name=image_name,
                system=system,
                desc=''
            )

            server = outputs.ServerDetailOutputServer(
                uuid=vm.config.instanceUuid,
                name=vm.name,
                ram=vm.summary.config.memorySizeMB,
                vcpu=vm.summary.config.numCpu,
                ip=ip,
                image=image,
                creation_time=helpers.iso_to_datetime(vm.config.createDate),
                default_user='',
                default_password='',
                azone_id='',
                disk_size=0
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
        try:
            service_instance = self._get_connect()
            vm = self._get_instance(conn=service_instance, instance_id=params.instance_id,
                                    instance_name=params.instance_name)
            if not vm:
                return outputs.ServerActionOutput()
            if format(vm.runtime.powerState) == "poweredOn":
                task = vm.PowerOffVM_Task()
                WaitForTask(task=task, si=service_instance)
            task = vm.Destroy_Task()
            WaitForTask(task=task, si=service_instance)
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
            vm = self._get_instance(conn=service_instance, instance_id=params.instance_id,
                                    instance_name=params.instance_name)
            if not vm:
                return outputs.ServerActionOutput()
            if params.action == inputs.ServerAction.START:
                task = vm.PowerOn()
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.SHUTDOWN:
                task = vm.PowerOffVM_Task()
                return outputs.ServerActionOutput()
            elif params.action in [inputs.ServerAction.DELETE, inputs.ServerAction.DELETE_FORCE]:
                if format(vm.runtime.powerState) == "poweredOn":
                    task = vm.PowerOffVM_Task()
                    WaitForTask(task=task, si=service_instance)
                task = vm.Destroy_Task()
                WaitForTask(task=task, si=service_instance)
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.POWER_OFF:
                task = vm.PowerOffVM_Task()
                return outputs.ServerActionOutput()
            elif params.action == inputs.ServerAction.REBOOT:
                task = vm.ResetVM_Task()
                return outputs.ServerActionOutput()
            else:
                return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))
        except Exception as e:
            return outputs.ServerActionOutput(ok=False, error=exceptions.Error('server action failed'))

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        status_map = {
            'running': outputs.ServerStatus.RUNNING,
            'notRunning': outputs.ServerStatus.SHUTOFF,
            'poweredOn': outputs.ServerStatus.RUNNING,
            'poweredOff': outputs.ServerStatus.SHUTOFF,
            'suspended': outputs.ServerStatus.PMSUSPENDED,
            'unknown': outputs.ServerStatus.NOSTATE,
        }
        try:
            service_instance = self._get_connect()
            vm = self._get_instance(conn=service_instance, instance_id=params.instance_id,
                                    instance_name=params.instance_name)
            if not vm:
                return outputs.ServerStatusOutput(status=outputs.ServerStatus.MISS,
                                                  status_mean=outputs.ServerStatus.get_mean(outputs.ServerStatus.MISS))

            state = vm.guest.guestState
            if state not in status_map:
                state = vm.runtime.powerState
                if state not in status_map:
                    state = 'unknown'

            status_code = status_map[state]
            status_mean = outputs.ServerStatus.get_mean(status_code)
            return outputs.ServerStatusOutput(status=status_code, status_mean=status_mean)
        except Exception as e:
            return outputs.ServerStatusOutput(ok=False, error=exceptions.Error('get server status failed'),
                                              status=outputs.ServerStatus.NOSTATE, status_mean='')

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        try:
            service_instance = self._get_connect()
            vm = self._get_instance(conn=service_instance, instance_id=params.instance_id,
                                    instance_name=params.instance_name)
            x = vm.AcquireTicket("webmks")
            vnc_url = "wss://" + str(x.host) + ":" + str(x.port) + "/ticket/" + str(x.ticket)
            return outputs.ServerVNCOutput(vnc=outputs.ServerVNCOutputVNC(url=vnc_url))
        except Exception as e:
            return outputs.ServerVNCOutput(ok=False, error=exceptions.Error('get vnc failed'), vnc=None)

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        try:
            service_instance = self._get_connect()
            content = service_instance.RetrieveContent()
            templates_folder = helpers.search_for_obj(content, [vim.Folder], name='templates')
            all_vm = helpers.get_all_obj(content, [vim.VirtualMachine], folder=templates_folder)
            result = []
            for vm in all_vm.values():
                if vm.config.template == True:
                    default_username = ''
                    default_password = ''
                    for field_value in vm.value:
                        for field in vm.availableField:
                            if field.name == 'default_user' and field.key == field_value.key:
                                default_username = field_value.value
                            elif field.name == 'default_password' and field.key == field_value.key:
                                default_password = field_value.value
                    disk_size = vm.storage.perDatastoreUsage[0].unshared / (1024 * 1024 * 1024)  # byte大小转GB
                    img_obj = outputs.ListImageOutputImage(
                        _id=vm.name, name=vm.name,
                        system=helpers.get_system_name(vm),
                        desc=vm.config.guestFullName,
                        system_type=helpers.get_system_type(vm),
                        creation_time=vm.config.createDate,
                        default_username=default_username, default_password=default_password,
                        min_sys_disk_gb=disk_size, min_ram_mb=0
                    )
                    result.append(img_obj)
            return outputs.ListImageOutput(images=result)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error(f'list image failed, {str(e)}'), images=[])

    def image_detail(self, params: inputs.ImageDetailInput, **kwargs):
        """
        查询镜像信息
        :return:
            output.ImageDetailOutput()
        """
        image_id = params.image_id
        r = self.list_images(params=inputs.ListImageInput(region_id=params.region_id))
        if not r.ok:
            return outputs.ImageDetailOutput(ok=False, error=r.error, image=None)

        for img in r.images:
            if img.id == image_id:
                return outputs.ImageDetailOutput(image=img)

        return outputs.ImageDetailOutput(ok=False, error=exceptions.ResourceNotFound(), image=None)

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        try:
            service_instance = self._get_connect()
            content = service_instance.RetrieveContent()
            all_networks = helpers.get_all_obj(content, [vim.Network])
            result = []
            for net in all_networks.values():
                public = False
                net_data_center = net.parent.parent.name
                new_net_name = net.name + '(' + net_data_center + ')'
                new_net = outputs.ListNetworkOutputNetwork(_id=net.name, name=new_net_name, public=public,
                                                           segment='0.0.0.0')
                if params.azone_id and net_data_center != params.azone_id:
                    continue
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
            content = service_instance.RetrieveContent()
            network = helpers.get_obj(content, [vim.Network], params.network_id)

            new_net = outputs.NetworkDetail(_id=params.network_id, name=params.network_id, public=False,
                                            segment='0.0.0.0')

            return outputs.NetworkDetailOutput(network=new_net)
        except exceptions.Error as e:
            return outputs.NetworkDetailOutput(ok=False, error=exceptions.Error(str(e)), network=None)

    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput):
        try:
            zones = []
            service_instance = self._get_connect()
            content = service_instance.RetrieveContent()
            datacenters = helpers.get_all_obj(content, [vim.Datacenter])
            for center in datacenters.values():
                zones.append(outputs.AvailabilityZone(_id=str(center.name), name=center.name))
            return outputs.ListAvailabilityZoneOutput(zones)
        except Exception as e:
            return outputs.ListAvailabilityZoneOutput(ok=False, error=exceptions.Error(str(e)), zones=None)