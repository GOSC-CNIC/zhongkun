"""
适配器各接口输出类定义
"""
from collections import namedtuple
from datetime import datetime


AuthenticateOutputHeader = namedtuple('AuthHeaderClass', ['header_name',         # example: 'Authorization'
                                                 'header_value'         # example: 'Token xxx', 'JWT xxx'
                                                 ])
AuthenticateOutputQuery = namedtuple('AuthQueryClass', ['query_name',            # example: 'token', 'jwt'
                                               'query_value'
                                               ])
AuthenticateOutput = namedtuple('AuthClass', ['style',       # 'token', 'jwt', ...
                                     'token',       # token value
                                     'header',      # AuthHeaderClass()
                                     'query',       # AuthQueryClass(); None if unsupported
                                     'expire',      # expire timestamp; type: int
                                     'username',
                                     'password'
                                     ])


class CreateServerOutputServerImage:
    def __init__(self, name: str, system: str, **kwargs):
        """
        :param name: 镜像名称
        :param system: 镜像系统，Windows10 64bit, Centos8 64bit, Ubuntu2004 ...
        """
        self.name = name
        self.system = system


class CreateServerOutputServerIP:
    def __init__(self, ipv4: str, public_ipv4: bool, **kwargs):
        """
        :param ipv4: ipv4 of server
        :param public_ipv4: ipv4是否是公网ip; True(公网)，False(私网)
        """
        self.ipv4 = ipv4
        self.public_ipv4 = public_ipv4


class CreateServerOutputServer:
    def __init__(self, uuid: str, ram: int, vcpu: int, image: CreateServerOutputServerImage,
                 ip: CreateServerOutputServerIP, creation_time: datetime, **kwargs):
        """
        :param uuid: id of server; type: str
        :param image: image of server; type: CreateServerOutputServerImage
        :param vcpu: vcpu of server; type: int
        :param ram: ram of server; type: int
        :param ip: ip of server; type: CreateServerOutputServerIP
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


class CreateServerOutput:
    def __init__(self, server: CreateServerOutputServer, **kwargs):
        """
        :param server: server; type: CreateServerOutputServer
        :param name: server name; type: str
        """
        self.server = server


