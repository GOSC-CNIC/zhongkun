"""
适配器各接口输出类定义
"""
from collections import namedtuple
from datetime import datetime

from .exceptions import Error


class ServerStatus:
    NOSTATE = 0     # no state
    RUNNING = 1     # the domain is running
    BLOCKED = 2     # the domain is blocked on resource
    PAUSED = 3      # the domain is paused by user
    SHUTDOWN = 4    # the domain is being shut down
    SHUTOFF = 5     # the domain is shut off
    CRASHED = 6     # the domain is crashed
    PMSUSPENDED = 7  # the domain is suspended by guest power management
    HOST_DOWN = 9   # host connect failed
    MISS = 10       # domain miss
    BUILDING = 11    # The domain is being built
    BUILT_FAILED = 12    # Failed to build the domain
    ERROR = 13          # error

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
        ERROR: 'error'
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


AuthenticateOutputHeader = namedtuple('AuthHeaderClass', ['header_name',         # example: 'Authorization'
                                                          'header_value'         # example: 'Token xxx', 'JWT xxx'
                                                          ])
AuthenticateOutputQuery = namedtuple('AuthQueryClass', ['query_name',            # example: 'token', 'jwt'
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
                 header: AuthenticateOutputHeader, query: AuthenticateOutputQuery,
                 username: str, password: str, **kwargs):
        """
        :param style: 'token', 'jwt', ...
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
        super().__init__(**kwargs)


class ServerImage:
    def __init__(self, _id: str, name: str, system: str, desc: str, **kwargs):
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
    def __init__(self, ipv4: str, public_ipv4: bool, **kwargs):
        """
        :param ipv4: ipv4 of server
        :param public_ipv4: ipv4是否是公网ip; True(公网)，False(私网)
        """
        self.ipv4 = ipv4
        self.public_ipv4 = public_ipv4


class ServerCreateOutputServer:
    def __init__(self, uuid: str, default_user: str, default_password: str, **kwargs):
        """
        :param uuid: id of server; type: str
        """
        self.uuid = uuid
        self.default_user = default_user
        self.default_password = default_password


class ServerCreateOutput(OutputBase):
    def __init__(self, server: ServerCreateOutputServer, **kwargs):
        """
        :param server: server; type: CreateServerOutputServer
        """
        self.server = server
        super().__init__(**kwargs)


class ServerDetailOutputServer:
    def __init__(self, uuid: str, ram: int, vcpu: int, image: ServerImage,
                 ip: ServerIP, creation_time: datetime, default_user: str,
                 default_password: str, **kwargs):
        """
        :param uuid: id of server; type: str
        :param image: image of server
        :param vcpu: vcpu of server; type: int
        :param ram: ram of server; type: int
        :param ip: ip of server
        :param creation_time: creation time of server; type: datetime
        :param default_user: login username
        :param default_password: login password
        :param name: name of server; type: str
        """
        self.uuid = uuid
        self.image = image
        self.vcpu = vcpu
        self.ram = ram
        self.ip = ip
        self.creation_time = creation_time
        self.default_user = default_user
        self.default_password = default_password
        self.name = kwargs.get('name', None)


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
    def __init__(self, server_id: str, image_id: str, default_user: str = None, default_password: str = None, **kwargs):
        """
        :param server_id: 云服务器实例id
        :param image_id: 系统镜像id; type: str; required: True
        :param default_user: login username
        :param default_password: login password
        """
        self.server_id = server_id
        self.image_id = image_id
        self.default_user = default_user if default_user else ''
        self.default_password = default_password if default_password else ''
        super().__init__(**kwargs)


class ListImageOutputImage:
    def __init__(self, id: str, name: str, system: str, system_type: str, creation_time: datetime,
                 default_username: str, default_password: str, **kwargs):
        """
        :param id:
        :param name: 镜像名称
        :param system: 镜像系统，Windows10 64bit, Centos8 64bit, Ubuntu2004 ...
        :param system_type: 系统类型，Windows, Linux, MacOS, Android, ...
        :param creation_time: 镜像创建时间
        :param desc: 镜像描述
        :param default_username: 初始默认登录用户名
        :param default_password: 初始默认登录用户密码
        """
        self.id = id
        self.name = name
        self.system = system
        self.system_type = system_type
        self.creation_time = creation_time
        self.desc = kwargs.get('desc', '')
        self.default_user = default_username
        self.default_password = default_password


class ListImageOutput(OutputBase):
    def __init__(self, images: list, **kwargs):
        """
        :param images: [ListImageOutputImage(), ]
        """
        self.images = images
        super().__init__(**kwargs)


class ListNetworkOutputNetwork:
    def __init__(self, id: str, name: str, public: bool, segment: str, **kwargs):
        """
        :param id:
        :param name: 子网名称
        :param public: 公网（True）；私网（False）
        :param segment: 网段
        """
        self.id = id
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


class VolumeStoragePool:
    def __init__(self, name: str,
                 total_capacity_gb: str = 'unknown',
                 free_capacity_gb: str = 'unknown',
                 max_size_limit_gb: str = 'unknown'):
        """
        :param name: 存储池名称
        :param total_capacity_gb: 总存储容量，单位Gb
        :param free_capacity_gb: 可用存储容量，单位Gb
        :param max_size_limit_gb: 一个卷volume最大容量限制，单位Gb
        """
        self.name = name
        self.total_capacity_gb = total_capacity_gb
        self.free_capacity_gb = free_capacity_gb
        self.max_size_limit_gb = max_size_limit_gb


class ListVolumeStoragePoolsOutput(OutputBase):
    def __init__(self, pools: list, **kwargs):
        self.pools = pools      # DiskStoragePool
        super().__init__(**kwargs)


class StorageVolume:
    """
    A base StorageVolume class to derive from.
    """

    def __init__(self,
                 id,  # type: str
                 name,  # type: str
                 size,  # type: int
                 driver,  # type: NodeDriver
                 state=None,  # type: Optional[StorageVolumeState]
                 extra=None  # type: Optional[Dict]
                 ):
        """
        :param id: Storage volume ID.
        :type id: ``str``
        :param name: Storage volume name.
        :type name: ``str``
        :param size: Size of this volume (in GB).
        :type size: ``int``
        :param driver: Driver this image belongs to.
        :type driver: :class:`.NodeDriver`
        :param state: Optional state of the StorageVolume. If not
                      provided, will default to UNKNOWN.
        :type state: :class:`.StorageVolumeState`
        :param extra: Optional provider specific attributes.
        :type extra: ``dict``
        """
        self.id = id
        self.name = name
        self.size = size
        self.driver = driver
        self.extra = extra
        self.state = state

    def attach(self, node, device=None):
        """
        Attach this volume to a node.
        :param node: Node to attach volume to
        :type node: :class:`.Node`
        :param device: Where the device is exposed,
                            e.g. '/dev/sdb (optional)
        :type device: ``str``
        :return: ``True`` if attach was successful, ``False`` otherwise.
        :rtype: ``bool``
        """
        return self.driver.attach_volume(node=node, volume=self, device=device)

    def detach(self):
        """
        Detach this volume from its node
        :return: ``True`` if detach was successful, ``False`` otherwise.
        :rtype: ``bool``
        """
        return self.driver.detach_volume(volume=self)

    def destroy(self):
        """
        Destroy this storage volume.
        :return: ``True`` if destroy was successful, ``False`` otherwise.
        :rtype: ``bool``
        """

        return self.driver.destroy_volume(volume=self)

    def __repr__(self):
        return '<StorageVolume id=%s size=%s driver=%s>' % (
               self.id, self.size, self.driver.name)

