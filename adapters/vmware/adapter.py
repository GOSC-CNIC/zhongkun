from datetime import datetime, timedelta, timezone

import uuid
import re
from pytz import utc

from adapters.base import BaseAdapter
from adapters import inputs
from adapters import outputs

from adapters import exceptions

import atexit

from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from pyVim.task import WaitForTask


datetime_re = re.compile(
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
    r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
    r'(?P<tzinfo>Z|[+-]\d{2}(?::?\d{2})?)?$'
)


def get_fixed_timezone(offset):
    """Return a tzinfo instance with a fixed offset from UTC."""
    if isinstance(offset, timedelta):
        offset = offset.total_seconds() // 60
    sign = '-' if offset < 0 else '+'
    hhmm = '%02d%02d' % divmod(abs(offset), 60)
    name = sign + hhmm
    return timezone(timedelta(minutes=offset), name)


def parse_datetime(value):
    """Parse a string and return a datetime.datetime.

    This function supports time zone offsets. When the input contains one,
    the output uses a timezone with a fixed offset from UTC.

    Raise ValueError if the input is well formatted but not a valid datetime.
    Return None if the input isn't well formatted.
    """
    match = datetime_re.match(value)
    if match:
        kw = match.groupdict()
        kw['microsecond'] = kw['microsecond'] and kw['microsecond'].ljust(6, '0')
        tzinfo = kw.pop('tzinfo')
        if tzinfo == 'Z':
            tzinfo = utc
        elif tzinfo is not None:
            offset_mins = int(tzinfo[-2:]) if len(tzinfo) > 3 else 0
            offset = 60 * int(tzinfo[1:3]) + offset_mins
            if tzinfo[0] == '-':
                offset = -offset
            tzinfo = get_fixed_timezone(offset)
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        kw['tzinfo'] = tzinfo
        return datetime(**kw)


def iso_to_datetime(value, default=datetime(year=1, month=1, day=1, hour=0, minute=0, second=0, tzinfo=utc)):
    try:
        parsed = parse_datetime(value)
        if parsed is not None:
            return default
    except (ValueError, TypeError):
        return default


"""
 Get the vsphere object associated with a given text name
"""


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name.lower() == name.lower():
            obj = c
            break
    return obj


"""
 Get the vsphere object associated with a given text name
"""


def get_obj_by_uuid(content, _uuid):
    obj = content.searchIndex.FindByUuid(None, _uuid, True, True)
    return obj


"""
 Get the vsphere object associated with a given text name
"""


def get_all_obj(content, vimtype):
    result = []
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        result.append(c)
    return result


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
            service_instance = SmartConnectNoSSL(host=self.endpoint_url,
                                                 user=username,
                                                 pwd=password,
                                                 port=int(443))
            atexit.register(Disconnect, service_instance)
            expire = (datetime.utcnow() + timedelta(hours=1)).timestamp()
            auth = outputs.AuthenticateOutput(style='token', token='', header=None, query=None,
                                              expire=int(expire), username=username, password=password,
                                              vmconnect=service_instance)
        except Exception as e:
            raise exceptions.AuthenticationFailed(message=str(e))

        self.auth = auth
        return auth

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        try:
            vm_name = 'gosc-instance-' + str(uuid.uuid1())
            deploy_settings = {'template': 'centos8_gui', 'hostname': 'gosc_003', 'ips': '10.0.200.243',
                               'cpus': params.vcpu, 'mem': params.ram, "new_vm_name": vm_name,
                               'template_name': params.image_id}

            # connect to vCenter server
            service_instance = self.auth.kwargs['vmconnect']

            # add a clean up routine
            atexit.register(Disconnect, service_instance)
            content = service_instance.RetrieveContent()
            datacenter = get_obj(content, [vim.Datacenter], 'Datacenter')
            destfolder = datacenter.vmFolder
            cluster = get_obj(content, [vim.ClusterComputeResource], 'gosc_cluster')
            resource_pool = cluster.resourcePool  # use same root resource pool that my desired cluster uses
            datastore = get_obj(content, [vim.Datastore], 'datastore1')
            template_vm = get_obj(content, [vim.VirtualMachine], deploy_settings["template_name"])
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
            nic.device.backing.network = get_obj(content, [vim.Network], params.network_id)
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
                uuid=vm_name
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
            service_instance = self.auth.kwargs['vmconnect']
            VM = get_obj(service_instance.content, [vim.VirtualMachine], params.server_id)
            try:
                server_ip = {'ipv4': VM.guest.ipAddress, 'public_ipv4': None}
            except Exception as e:
                server_ip = {'ipv4': None, 'public_ipv4': None}

            ip = outputs.ServerIP(**server_ip)
            try:
                image_name = params.server_id.split('-&&image&&-')[1]
            except Exception as e:
                image_name = None

            image = outputs.ServerImage(
                name=image_name,
                system=VM.config.guestId
            )

            server = outputs.ServerDetailOutputServer(
                uuid=params.server_id,
                ram=VM.summary.config.memorySizeMB,
                vcpu=VM.summary.config.numCpu,
                ip=ip,
                image=image,
                creation_time=iso_to_datetime(VM.config.createDate)
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
            service_instance = self.auth.kwargs['vmconnect']
            vm = get_obj(service_instance.content, [vim.VirtualMachine], params.server_id)
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
            service_instance = self.auth.kwargs['vmconnect']
            vm = get_obj(service_instance.content, [vim.VirtualMachine], params.server_id)
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
            'running': 1,
            'unknown': 0,
            'notRunning': 4,
        }
        try:
            service_instance = self.auth.kwargs['vmconnect']
            vm = get_obj(service_instance.content, [vim.VirtualMachine], params.server_id)
            if not vm:
                return outputs.ServerStatusOutput(status=outputs.ServerStatus.MISS,
                                                  status_mean=outputs.ServerStatus.get_mean(outputs.ServerStatus.MISS))
            status_code = status_map[vm.guest.guestState]
            if status_code not in outputs.ServerStatus():
                status_code = outputs.ServerStatus.NOSTATE
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
            service_instance = self.auth.kwargs['vmconnect']
            vm = get_obj(service_instance.content, [vim.VirtualMachine], params.server_id)
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
            service_instance = self.auth.kwargs['vmconnect']
            content = service_instance.RetrieveContent()
            all_vm = get_all_obj(content, [vim.VirtualMachine])
            result = []
            for vm in all_vm:
                if vm.config.template == True:
                    img_obj = outputs.ListImageOutputImage(id=vm.name, name=vm.name, system=vm.config.guestFullName,
                                                           desc=vm.config.guestFullName,
                                                           system_type=vm.config.guestId,
                                                           creation_time=vm.config.createDate)
                    result.append(img_obj)
            return outputs.ListImageOutput(images=result)
        except Exception as e:
            return outputs.ListImageOutput(ok=False, error=exceptions.Error('list image failed'), images=[])

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
        """
        try:
            service_instance = self.auth.kwargs['vmconnect']
            content = service_instance.RetrieveContent()
            all_networks = get_all_obj(content, [vim.Network])
            result = []
            for net in all_networks:
                public = False
                new_net = outputs.ListNetworkOutputNetwork(id=net.name, name=net.name, public=public,
                                                           segment='0.0.0.0')
                result.append(new_net)
            return outputs.ListNetworkOutput(networks=result)

        except Exception as e:
            return outputs.ListNetworkOutput(ok=False, error=exceptions.Error('list networks failed'), networks=[])

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        try:
            service_instance = self.auth.kwargs['vmconnect']
            content = service_instance.RetrieveContent()
            network = get_obj(content, [vim.Network], params.network_id)

            new_net = outputs.NetworkDetail(id=params.network_id, name=params.network_id, public=False,
                                            segment='0.0.0.0')

            return outputs.NetworkDetailOutput(network=new_net)
        except exceptions.Error as e:
            return outputs.NetworkDetailOutput(ok=False, error=exceptions.Error(str(e)), network=None)
