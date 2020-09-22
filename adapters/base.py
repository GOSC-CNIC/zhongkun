"""

"""
from . import inputs
from . import outputs


class BaseAdapter:
    """
    不同类型的服务平台的api适配器的基类
    """
    adapter_name = 'adapter'

    def __str__(self):
        return self.adapter_name

    def __init__(self,
                 endpoint_url: str,
                 api_version: str,
                 auth: outputs.AuthenticateOutput = None,
                 *args, **kwargs
                 ):
        self.endpoint_url = endpoint_url
        self.auth = auth
        self.api_version = api_version

    def authenticate(self, username, password):
        """
        认证获取 Token

        :param username:
        :param password:
        :return:
            outputs.AuthenticateOutput()

        :raises: exceptions.AuthenticationFailed
        """
        raise NotImplementedError('`authenticate()` must be implemented.')

    def server_create(self, params: inputs.ServerCreateInput, **kwargs):
        """
        创建虚拟服务器
        :return:
            outputs.ServerCreateOutput()
        """
        raise NotImplementedError('`server_create()` must be implemented.')

    def server_delete(self, params: inputs.ServerDeleteInput, **kwargs):
        """
        删除虚拟服务器
        :return:
            outputs.ServerDeleteOutput()
        """
        raise NotImplementedError('`server_delete()` must be implemented.')

    def server_action(self, params: inputs.ServerActionInput, **kwargs):
        """
        操作虚拟主机
        :return:
            outputs.ServerActionOutput()
        """
        raise NotImplementedError('`server_action()` must be implemented.')

    def server_status(self, params: inputs.ServerStatusInput, **kwargs):
        """
        :return:
            outputs.ServerStatusOutput()
        """
        raise NotImplementedError('`server_status()` must be implemented.')

    def server_vnc(self, params: inputs.ServerVNCInput, **kwargs):
        """
        :return:
            outputs.ServerVNCOutput()
        """
        raise NotImplementedError('`server_vnc()` must be implemented.')

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        raise NotImplementedError('`list_images()` must be implemented.')

    def list_networks(self, region_id: str, headers: dict = None):
        """
        列举子网

        :param region_id: 分中心id
        :param headers:
        :return:
        """
        raise NotImplementedError('`list_networks()` must be implemented.')

    def list_flavors(self, headers: dict = None):
        """
        列举配置样式

        :param headers:
        :return:
        """
        raise NotImplementedError('`list_flavors()` must be implemented.')

    def get_flavor(self, flavor_id, headers: dict = None):
        raise NotImplementedError('`get_flavor()` must be implemented.')

    def get_network(self, network_id, headers: dict = None):
        raise NotImplementedError('`get_network()` must be implemented.')


