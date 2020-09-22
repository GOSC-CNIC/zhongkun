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
    }

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


class ServerCreateOutputServerImage:
    def __init__(self, name: str, system: str, **kwargs):
        """
        :param name: 镜像名称
        :param system: 镜像系统，Windows10 64bit, Centos8 64bit, Ubuntu2004 ...
        """
        self.name = name
        self.system = system


class ServerCreateOutputServerIP:
    def __init__(self, ipv4: str, public_ipv4: bool, **kwargs):
        """
        :param ipv4: ipv4 of server
        :param public_ipv4: ipv4是否是公网ip; True(公网)，False(私网)
        """
        self.ipv4 = ipv4
        self.public_ipv4 = public_ipv4


class ServerCreateOutputServer:
    def __init__(self, uuid: str, ram: int, vcpu: int, image: ServerCreateOutputServerImage,
                 ip: ServerCreateOutputServerIP, creation_time: datetime, **kwargs):
        """
        :param uuid: id of server; type: str
        :param image: image of server; type: ServerCreateOutputServerImage
        :param vcpu: vcpu of server; type: int
        :param ram: ram of server; type: int
        :param ip: ip of server; type: ServerCreateOutputServerIP
        :param creation_time: creation time of server; type: datetime
        :param name: name of server; type: str
        """
        self.uuid = uuid
        self.image = image
        self.vcpu = vcpu
        self.ram = ram
        self.ip = ip
        self.creation_time = creation_time
        self.name = kwargs.get('name', None)


class ServerCreateOutput(OutputBase):
    def __init__(self, server: ServerCreateOutputServer, **kwargs):
        """
        :param server: server; type: CreateServerOutputServer
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


class ListImageOutputImage:
    def __init__(self, id: str, name: str, system: str, system_type: str, creation_time: datetime, **kwargs):
        """
        :param id:
        :param name: 镜像名称
        :param system: 镜像系统，Windows10 64bit, Centos8 64bit, Ubuntu2004 ...
        :param system_type: 系统类型，Windows, Linux, MacOS, Android, ...
        :param creation_time: 镜像创建时间
        :param desc: 镜像描述
        """
        self.id = id
        self.name = name
        self.system = system
        self.system_type = system_type
        self.creation_time = creation_time
        self.desc = kwargs.get('desc', '')


class ListImageOutput(OutputBase):
    def __init__(self, images: list, **kwargs):
        """
        :param images: [ListImageOutputImage(), ]
        """
        self.images = images
        super().__init__(**kwargs)
