"""
适配器各接口输入参数类定义
"""


class ServerAction:
    START = 'start'
    REBOOT = 'reboot'
    SHUTDOWN = 'shutdown'
    POWER_OFF = 'poweroff'
    DELETE = 'delete'
    DELETE_FORCE = 'delete_force'

    values = [START, REBOOT, SHUTDOWN, POWER_OFF, DELETE, DELETE_FORCE]


class InputBase:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return getattr(self._kwargs, attr)
        except AttributeError:
            return None


class AuthenticateInput(InputBase):
    def __init__(self, username: str, password: str, **kwargs):
        """
        :param username:
        :param password:
        :param domain:
        :param kwargs:
        """
        self.username = username
        self.password = password
        self.domain = kwargs.get('domain', 'default')
        super().__init__(**kwargs)


class ServerCreateInput(InputBase):
    def __init__(self, ram: int, vcpu: int, image_id: str, systemdisk_size: int, **kwargs):
        """
        :param ram: 内存大小，单位MiB; required: True
        :param vcpu: 虚拟CPU数; required: True
        :param image_id: 系统镜像id; type: str; required: True
        :param systemdisk_size: 系统盘大小，单位GB，默认未指定大小，各适配器根据各自的情况定义默认大小; required: False
        :param public_ip: 指定分配公网(True)或私网(False)IP; type: bool; required: False
        :param region_id: 区域/分中心id; type: str; required: False
        :param network_id: 子网id; type: str; required: False
        :param remarks: 备注信息; type: str; required: False
        :param azone_id: availability zone id; type: str
        """
        self.ram = ram
        self.vcpu = vcpu
        self.image_id = image_id
        self.systemdisk_size = systemdisk_size
        self.public_ip = kwargs.get('public_ip', None)
        self.region_id = kwargs.get('region_id', None)
        self.network_id = kwargs.get('network_id', None)
        self.remarks = kwargs.get('remarks', None)
        self.azone_id = kwargs.get('azone_id', None)
        self.flavor_id = kwargs.get('flavor_id', None)
        super().__init__(**kwargs)


class ServerIdNameInput(InputBase):
    def __init__(self, instance_id: str, instance_name: str = None, **kwargs):
        """
        :param instance_id: 云服务器实例id
        :param instance_name: 云服务器实例name
        """
        self.instance_id = instance_id
        self.instance_name = instance_name
        super().__init__(**kwargs)


class ServerActionInput(ServerIdNameInput):
    def __init__(self, action: str, **kwargs):
        """
        :param action: 执行的操作；only value in ServerAction.values
        """
        self.action = action
        super().__init__(**kwargs)


class ServerStatusInput(ServerIdNameInput):
    def __init__(self, **kwargs):
        """
        """
        super().__init__(**kwargs)


class ServerDeleteInput(ServerIdNameInput):
    def __init__(self, force: bool = False, **kwargs):
        """
        :param force: True(强制删除); False(删除)
        """
        self.force = force
        super().__init__(**kwargs)


class ServerVNCInput(ServerIdNameInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ServerDetailInput(ServerIdNameInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ServerRebuildInput(ServerIdNameInput):
    def __init__(self, image_id: str, **kwargs):
        """
        :param image_id: 系统镜像id; type: str; required: True
        """
        self.image_id = image_id
        super().__init__(**kwargs)


class ListImageInput(InputBase):
    def __init__(self, region_id: str, page_num: int, page_size: int, flavor_id: str = '', **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.region_id = region_id
        self.page_num = page_num
        self.page_size = page_size
        self.flavor_id = flavor_id
        super().__init__(**kwargs)


class ListAzoneInput(InputBase):
    def __init__(self, region_id: str, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.region_id = region_id
        super().__init__(**kwargs)


class ImageDetailInput(InputBase):
    def __init__(self, image_id: str, region_id: str, **kwargs):
        """
        :param image_id: 镜像id; type: str; required: True
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.image_id = image_id
        self.region_id = region_id
        super().__init__(**kwargs)


class ListNetworkInput(InputBase):
    def __init__(self, region_id: str, public: bool = None, azone_id: str = None, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        :param public: 网络类型筛选条件；True(公网网段);False(私网网段);默认None(忽略)
        :param azone_id: 可用区编码
        """
        self.region_id = region_id
        if public not in [None, True, False]:
            raise ValueError('None、True or False')
        self.public = public
        self.azone_id = azone_id
        super().__init__(**kwargs)


class NetworkDetailInput(InputBase):
    def __init__(self, network_id: str, azone_id: str = None, **kwargs):
        """
        :param network_id: 网络网段id; type: str; required: False
        """
        self.azone_id = azone_id
        self.network_id = network_id
        super().__init__(**kwargs)


class ListAvailabilityZoneInput(InputBase):
    def __init__(self, region_id: str, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.region_id = region_id
        super().__init__(**kwargs)


class DiskCreateInput(InputBase):
    def __init__(self, region_id: str, azone_id: str, size_gib: int, description: str, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.region_id = region_id
        self.azone_id = azone_id
        self.size_gib = size_gib  # Gb
        self.description = description  # 备注，描述
        super().__init__(**kwargs)


class DiskDeleteInput(InputBase):
    def __init__(self, disk_id: str, disk_name: str, **kwargs):
        self.disk_id = disk_id
        self.disk_name = disk_name
        super().__init__(**kwargs)


class DiskAttachInput(InputBase):
    def __init__(self, instance_id: str, disk_id: str, mountpoint: str = None, **kwargs):
        """
        :param instance_id: 云主机id
        :param disk_id: 云硬盘id
        :param mountpoint: 挂载点，例如 "/dev/vdc"
        """
        self.instance_id = instance_id
        self.disk_id = disk_id
        self.mountpoint = mountpoint
        super().__init__(**kwargs)


class DiskDetachInput(InputBase):
    def __init__(self, instance_id: str, disk_id: str, **kwargs):
        """
        :param instance_id: 云主机id
        :param disk_id: 云硬盘id
        """
        self.instance_id = instance_id
        self.disk_id = disk_id
        super().__init__(**kwargs)


class DiskDetailInput(InputBase):
    def __init__(self, disk_id: str, disk_name: str, **kwargs):
        self.disk_id = disk_id
        self.disk_name = disk_name
        super().__init__(**kwargs)
