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
    def __init__(self, ram: int, vcpu: int, image_id: str, **kwargs):
        """
        :param ram: 内存大小，单位GB; required: True
        :param vcpu: 虚拟CPU数; required: True
        :param image_id: 系统镜像id; type: str; required: True
        :param public_ip: 指定分配公网(True)或私网(False)IP; type: bool; required: False
        :param region_id: 区域/分中心id; type: str; required: False
        :param network_id: 子网id; type: str; required: False
        :param remarks: 备注信息; type: str; required: False
        """
        self.ram = ram
        self.vcpu = vcpu
        self.image_id = image_id
        self.public_ip = kwargs.get('public_ip', None)
        self.region_id = kwargs.get('region_id', None)
        self.network_id = kwargs.get('network_id', None)
        self.remarks = kwargs.get('remarks', None)
        super().__init__(**kwargs)


class ServerActionInput(InputBase):
    def __init__(self, server_id: str, action: str, **kwargs):
        """
        :param server_id: 云服务器实例id
        :param action: 执行的操作；only value in ServerAction.values
        """
        self.server_id = server_id
        self.action = action
        super().__init__(**kwargs)


class ServerStatusInput(InputBase):
    def __init__(self, server_id: str, **kwargs):
        """
        :param server_id: 云服务器实例id
        """
        self.server_id = server_id
        super().__init__(**kwargs)


class ServerDeleteInput(InputBase):
    def __init__(self, server_id: str, force: bool = False, **kwargs):
        """
        :param server_id: 云服务器实例id
        :param force: True(强制删除); False(删除)
        """
        self.server_id = server_id
        self.force = force
        super().__init__(**kwargs)


class ServerVNCInput(InputBase):
    def __init__(self, server_id: str, **kwargs):
        """
        :param server_id: 云服务器实例id
        """
        self.server_id = server_id
        super().__init__(**kwargs)


class ServerDetailInput(InputBase):
    def __init__(self, server_id: str, **kwargs):
        """
        :param server_id: 云服务器实例id
        """
        self.server_id = server_id
        super().__init__(**kwargs)


class ListImageInput(InputBase):
    def __init__(self, region_id: str, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        """
        self.region_id = region_id
        super().__init__(**kwargs)


class ListNetworkInput(InputBase):
    def __init__(self, region_id: str, public: bool = None, **kwargs):
        """
        :param region_id: 区域/分中心id; type: str; required: False
        :param public: 网络类型筛选条件；True(公网网段);False(私网网段);默认None(忽略)
        """
        self.region_id = region_id
        self.public = public
        super().__init__(**kwargs)


class NetworkDetailInput(InputBase):
    def __init__(self, network_id: str, **kwargs):
        """
        :param network_id: 网络网段id; type: str; required: False
        """
        self.network_id = network_id
        super().__init__(**kwargs)


class DiskCreateInput(InputBase):
    def __init__(self, size: int, description: str, **kwargs):
        self.size = size                    # Gb
        self.description = description      # 备注，描述
        super().__init__(**kwargs)
