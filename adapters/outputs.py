"""
适配器各接口输出类定义
"""
from typing import List
from collections import namedtuple
from datetime import datetime

from .exceptions import Error


class ServerStatus:
    NOSTATE = 0  # no state
    RUNNING = 1  # the domain is running
    BLOCKED = 2  # the domain is blocked on resource
    PAUSED = 3  # the domain is paused by user
    SHUTDOWN = 4  # the domain is being shut down
    SHUTOFF = 5  # the domain is shut off
    CRASHED = 6  # the domain is crashed
    PMSUSPENDED = 7  # the domain is suspended by guest power management
    HOST_DOWN = 9  # host connect failed
    MISS = 10  # domain miss
    BUILDING = 11  # The domain is being built
    BUILT_FAILED = 12  # Failed to build the domain
    ERROR = 13  # error
    REBUILDING = 14  # The domain is being built

    __status_map = {
        NOSTATE: 'no state',
        RUNNING: 'running',
        BLOCKED: 'blocked',
        PAUSED: 'paused',
        SHUTDOWN: 'shut down',
        SHUTOFF: 'shut off',
        CRASHED: 'crashed',
        PMSUSPENDED: 'suspended',
        HOST_DOWN: 'host connect failed',
        MISS: 'miss',
        BUILDING: 'building',
        BUILT_FAILED: 'built failed',
        ERROR: 'error',
        REBUILDING: 'rebuilding'
    }

    __normal_values = [
        RUNNING, BLOCKED, PAUSED, SHUTDOWN, SHUTOFF, CRASHED, PMSUSPENDED
    ]

    def __contains__(self, item):
        return item in self.__status_map

    @classmethod
    def values(cls):
        return cls.__status_map.values()

    @classmethod
    def keys(cls):
        return cls.__status_map.keys()

    @classmethod
    def get_mean(cls, status):
        if status not in cls.__status_map:
            status = cls.NOSTATE

        return cls.__status_map[status]

    @classmethod
    def status_map(cls):
        return cls.__status_map

    @classmethod
    def normal_values(cls):
        """
        server正常的运行状态值列表
        :return:
        """
        return cls.__normal_values


AuthenticateOutputHeader = namedtuple('AuthHeaderClass', ['header_name',  # example: 'Authorization'
                                                          'header_value'  # example: 'Token xxx', 'JWT xxx'
                                                          ])
AuthenticateOutputQuery = namedtuple('AuthQueryClass', ['query_name',  # example: 'token', 'jwt'
                                                        'query_value'
                                                        ])


class OutputBase:
    def __init__(self, ok: bool = True, error: Error = None, **kwargs):
        """
        :param ok: True(success); False(failed/error)
        :param error: Error() if ok == False else None
        :param kwargs:
        """
        self.ok = ok
        self.error = error
        self.kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return getattr(self._kwargs, attr)
        except AttributeError:
            return None


class AuthenticateOutput(OutputBase):
    def __init__(self, style: str, token: str, expire: int,
                 header: AuthenticateOutputHeader = None, query: AuthenticateOutputQuery = None,
                 username: str = '', password: str = '',
                 access_key: str = '', secret_key: str = '',
                 **kwargs):
        """
        :param style: 'token', 'jwt', 'key, ...
        :param token: token value
        :param expire: expire timestamp; type: int
        :param header: AuthenticateOutputHeader() or None
        :param query: AuthenticateOutputQuery() or None
        :param username:
        :param password:
        :param kwargs:
        """
        self.style = style
        self.token = token
        self.expire = expire
        self.header = header
        self.query = query
        self.username = username
        self.password = password
        self.access_key = access_key
        self.secret_key = secret_key
        super().__init__(**kwargs)


class ServerImage:
    def __init__(self, _id: str, name: str, system: str, desc: str):
        """
        :param _id: 镜像id
        :param name: 镜像名称
        :param system: 镜像系统，Windows10 64bit, Centos8 64bit, Ubuntu2004 ...
        :param desc: 镜像描述信息
        """
        self.id = _id
        self.name = name
        self.system = system
        self.desc = desc


class ServerIP:
    def __init__(self, ipv4: str, public_ipv4: bool):
        """
        :param ipv4: ipv4 of server
        :param public_ipv4: ipv4是否是公网ip; True(公网)，False(私网)
        """
        self.ipv4 = ipv4
        self.public_ipv4 = public_ipv4


class ServerCreateOutputServer:
    def __init__(self, uuid: str, name: str, default_user: str, default_password: str):
        """
        :param uuid: id of server; type: str
        """
        self.uuid = uuid
        self.name = name
        self.default_user = default_user
        self.default_password = default_password


class ServerCreateOutput(OutputBase):
    def __init__(self, server: ServerCreateOutputServer = None, **kwargs):
        """
        :param server: server; type: CreateServerOutputServer
        """
        self.server = server
        super().__init__(**kwargs)


class ServerDetailOutputServer:
    def __init__(self, uuid: str, name: str, ram: int, vcpu: int, image: ServerImage,
                 ip: ServerIP, creation_time: datetime, default_user: str,
                 default_password: str, azone_id: str, disk_size: int, **kwargs):
        """
        :param uuid: id of server; type: str
        :param image: image of server
        :param vcpu: vcpu of server; type: int
        :param ram: ram of server; type: int  Mb
        :param ip: ip of server
        :param creation_time: creation time of server; type: datetime
        :param default_user: login username
        :param default_password: login password
        :param name: name of server; type: str
        :param azone_id: availability zone id/code
        :param disk_size: system disk size GiB
        """
        self.uuid = uuid
        self.name = name
        self.image = image
        self.vcpu = vcpu
        self.ram = ram
        self.ip = ip
        self.creation_time = creation_time
        self.default_user = default_user
        self.default_password = default_password
        self.azone_id = azone_id
        self.disk_size = disk_size


class ServerDetailOutput(OutputBase):
    def __init__(self, server: ServerDetailOutputServer, **kwargs):
        """
        :param server: server
        """
        self.server = server
        super().__init__(**kwargs)


class ServerActionOutput(OutputBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ServerStatusOutput(OutputBase):
    def __init__(self, status: int, status_mean: str, **kwargs):
        """
        :param status:      server运行状态码
        :param status_mean: 状态码的意义
        """
        self.status = status
        self.status_mean = status_mean
        super().__init__(**kwargs)


class ServerDeleteOutput(OutputBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class ServerVNCOutputVNC:
    def __init__(self, url: str):
        self.url = url


class ServerVNCOutput(OutputBase):
    def __init__(self, vnc: ServerVNCOutputVNC, **kwargs):
        self.vnc = vnc
        super().__init__(**kwargs)


class ServerRebuildOutput(OutputBase):
    def __init__(self, instance_id: str, image_id: str, instance_name: str = '',
                 default_user: str = None, default_password: str = None, **kwargs):
        """
        :param instance_id: 云服务器实例id, required: True
        :param instance_name: 云服务器实例name, required: False, VMware required
        :param image_id: 系统镜像id; type: str; required: True
        :param default_user: login username
        :param default_password: login password
        """
        self.instance_id = instance_id
        self.instance_name = instance_name
        self.image_id = image_id
        self.default_user = default_user if default_user else ''
        self.default_password = default_password if default_password else ''
        super().__init__(**kwargs)


class ListImageOutputImage:
    def __init__(self, _id: str, name: str, release: str, version: str, architecture: str, system_type: str,
                 creation_time: datetime,
                 default_username: str, default_password: str, min_sys_disk_gb: int, min_ram_mb: int, **kwargs):
        """
        :param _id:
        :param name: 镜像名称
        :param release: 系统发行版本，取值空间为{Windows Desktop, Windows Server, Ubuntu, Fedora, Centos, Unknown}
        :param version: 系统发行编号（64字符内），取值空间为{win10,win11,2021,2019,2204,2004,36,37,7,8,9,....}
        :param architecture: 系统架构，取值空间为{x86-64,i386,arm-64,unknown}
        :param system_type: 系统类型，Windows, Linux, MacOS, Android, ...
        :param creation_time: 镜像创建时间
        :param desc: 镜像描述
        :param default_username: 初始默认登录用户名
        :param default_password: 初始默认登录用户密码
        :param min_sys_disk_gb: 需要最小系统盘大小
        :param min_ram_mb: 需要最小内存大小
        """
        self.id = _id
        self.name = name
        self.release = release
        self.version = version
        self.architecture = architecture
        self.system_type = system_type
        self.creation_time = creation_time
        self.desc = kwargs.get('desc', '')
        self.default_user = default_username
        self.default_password = default_password
        self.min_sys_disk_gb = min_sys_disk_gb
        self.min_ram_mb = min_ram_mb

        # 大小写转换格式化，将未识别的设置为Unknown，根据name匹配一下
        system_type_choices = {"windows": "Windows", "linux": "Linux", "unix": "Unix", "macos": "MacOS",
                               "unknown": "Unknown", "ubuntu": "Linux", "fedora": "Linux", "centos": "Linux"}
        release_choices = {"windows": "Windows Desktop", "windows desktop": "Windows Desktop",
                           "windows server": "Windows Server", "ubuntu": "Ubuntu", "fedora": "Fedora",
                           "centos": "Centos", "unknown": "Unknown"}
        architecture_choices = {"64 bit": "x86-64", "64-bit": "x86-64", "amd64": "x86-64", "64位": "x86-64",
                                "x64": "x86-64", "x86_64": "x86-64", "x86-64": "x86-64",
                                "i386": "i386",
                                "arm-64": "arm-64", "unknown": "Unknown"}
        tips = self.name + ' ' + self.version
        self.architecture = self._format_image_property(self.architecture, architecture_choices, tips)
        self.release = self._format_image_property(self.release, release_choices, tips)
        self.system_type = self._format_image_property(self.system_type, system_type_choices, tips)

    @staticmethod
    def _format_image_property(prop_value, prop_choices, tips):
        result = 'Unknown'
        if not isinstance(prop_value, str):
            return result

        prop_value = prop_value.lower()
        if prop_value != 'unknown' and prop_value in prop_choices.keys():
            result = prop_choices[prop_value]
        else:
            tips = tips.lower()
            for key in prop_choices.keys():
                if tips.find(key.lower()) != -1:
                    result = prop_choices[key]
                    break

        return result


class ListImageOutput(OutputBase):
    def __init__(self, images: List[ListImageOutputImage], count: int = 0, **kwargs):
        """
        :param images: [ListImageOutputImage(), ]
        """
        self.images = images
        self.count = count
        super().__init__(**kwargs)


class ImageDetailOutput(OutputBase):
    def __init__(self, image: ListImageOutputImage = None, **kwargs):
        """
        :param image: ListImageOutputImage()
        """
        self.image = image
        super().__init__(**kwargs)


class ListNetworkOutputNetwork:
    def __init__(self, _id: str, name: str, public: bool, segment: str, **kwargs):
        """
        :param _id:
        :param name: 子网名称
        :param public: 公网（True）；私网（False）
        :param segment: 网段
        """
        self.id = _id
        self.name = name
        self.public = public
        self.segment = segment
        super().__init__(**kwargs)


class ListNetworkOutput(OutputBase):
    def __init__(self, networks: list, **kwargs):
        """
        :param networks: [ListNetworkOutputNetwork(), ]
        """
        self.networks = networks
        super().__init__(**kwargs)


class NetworkDetail(ListNetworkOutputNetwork):
    pass


class NetworkDetailOutput(OutputBase):
    def __init__(self, network: NetworkDetail = None, **kwargs):
        self.network = network
        super().__init__(**kwargs)


class AvailabilityZone:
    def __init__(self, _id: str, name: str, available: bool = True):
        self.id = _id
        self.name = name
        self.available = available


class ListAvailabilityZoneOutput(OutputBase):
    def __init__(self, zones: List[AvailabilityZone] = None, **kwargs):
        self.zones = zones
        super().__init__(**kwargs)


class SimpleDisk:
    def __init__(self, disk_id: str, name: str):
        """
        :param disk_id: id of disk; type: str
        """
        self.disk_id = disk_id
        self.name = name


class DiskStatus:
    CREATING = 'creating'       # 正在创建
    IN_USE = 'in-use'           # 已附加到实例
    AVAILABLE = 'available'     # 创建完成，正常可用，已准备好附加到实例
    ATTACHING = 'attaching'     # 正在附加到实例
    DETACHING = 'detaching'     # 正在与实例分离
    EXTENDING = 'extending'     # 正在扩展卷
    ERROR = 'error'             # 错误
    UNKNOWN = 'unknown'         # 无状态，未知状态

    __status_map = {
        CREATING: 'The disk is being created.',
        IN_USE: 'The disk is attached to an instance.',
        AVAILABLE: 'The disk is ready to attach to an instance.',
        ATTACHING: 'The disk is attaching to an instance.',
        DETACHING: 'The disk is detaching from an instance.',
        EXTENDING: 'The disk is being extended.',
        ERROR: 'A error occurred.',

    }

    __normal_values = [
        IN_USE, AVAILABLE, ATTACHING, DETACHING, EXTENDING
    ]

    def __contains__(self, item):
        return item in self.__status_map

    @classmethod
    def values(cls):
        return cls.__status_map.values()

    @classmethod
    def keys(cls):
        return cls.__status_map.keys()

    @classmethod
    def normal_values(cls):
        return cls.__normal_values


class DetailDisk(SimpleDisk):
    def __init__(
            self, disk_id: str, name: str,
            size_gib: int,
            region_id: str, azone_id: str,
            creation_time: datetime,
            description: str,
            status: str,
            instance_id: str,
            device: str
    ):
        """
        :param disk_id: id of disk; type: str
        :param name:
        :param size_gib: 盘大小GiB
        :param region_id: 区域ID
        :param azone_id: 可用区ID
        :param creation_time: 盘创建时间
        :param description: 描述
        :param status: 盘状态
        :param instance_id: status=‘in-use’时，盘挂载的云主机id，未挂载时为空
        :param device: 盘挂载于的云主机时的挂载点、设备名称，例如/dev/xvdb；未挂载时为空
        """
        super().__init__(disk_id=disk_id, name=name)
        self.size_gib = size_gib
        self.region_id = region_id
        self.azone_id = azone_id
        self.creation_time = creation_time
        self.description = description
        self.status = status
        self.instance_id = instance_id
        self.device = device


class DiskCreateOutput(OutputBase):
    def __init__(self, disk: SimpleDisk, **kwargs):
        self.disk = disk
        super().__init__(**kwargs)


class DiskCreatePretendOutput(OutputBase):
    def __init__(self, result: bool, reason: str, **kwargs):
        """
        :param result: True: 满足创建云硬盘的条件；False: 无法满足云硬盘创建的条件
        :param reason: result is True，无法满足云硬盘创建的条件 原因描述
        """
        self.result = result
        self.reason = reason
        super().__init__(**kwargs)


class DiskDetailOutput(OutputBase):
    def __init__(self, disk: DetailDisk, **kwargs):
        self.disk = disk
        super().__init__(**kwargs)


class DiskDeleteOutput(OutputBase):
    pass


class DiskAttachOutput(OutputBase):
    pass


class DiskDetachOutput(OutputBase):
    pass


class DiskStoragePool:
    def __init__(
            self, pool_id: str, name: str,
            total_capacity_gb: int,
            free_capacity_gb: int,
            max_size_limit_gb: int,
            available: bool
    ):
        """
        :param pool_id:
        :param name: 存储池名称
        :param total_capacity_gb: 总存储容量，单位Gb
        :param free_capacity_gb: 可用存储容量，单位Gb
        :param max_size_limit_gb: 一个卷disk最大容量限制，单位Gb
        :param available: True: 可用；False: 不可用
        """
        self.pool_id = pool_id
        self.name = name
        self.total_capacity_gb = total_capacity_gb
        self.free_capacity_gb = free_capacity_gb
        self.max_size_limit_gb = max_size_limit_gb
        self.available = available


class ListDiskStoragePoolsOutput(OutputBase):
    def __init__(self, pools: List[DiskStoragePool], **kwargs):
        self.pools = pools  # DiskStoragePool
        super().__init__(**kwargs)
