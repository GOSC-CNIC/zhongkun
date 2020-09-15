"""
适配器各接口输入参数类定义
"""


class InputBase:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __getattr__(self, attr):
        try:
            return getattr(self._kwargs, attr)
        except AttributeError:
            return None


class CreateServerInput(InputBase):
    def __init__(self, ram: int, vcpu: int, image_id: str, **kwargs):
        """
        :param ram: 内存大小，单位GB; required: True
        :param vcpu: 虚拟CPU数; required: True
        :param image_id: 系统镜像id; type: str; required: True
        :param flavor_id: 配置样式id; type: str; required: False
        :param region_id: 区域/分中心id; type: str; required: False
        :param network_id: 子网id; type: str; required: False
        :param remarks: 备注信息; type: str; required: False
        """
        self.ram = ram
        self.vcpu = vcpu
        self.image_id = image_id
        self.flavor_id = kwargs.get('flavor_id', None)
        self.region_id = kwargs.get('region_id', None)
        self.network_id = kwargs.get('network_id', None)
        self.remarks = kwargs.get('remarks', None)
        super().__init__(**kwargs)


