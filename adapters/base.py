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
        self.endpoint_url = endpoint_url.rstrip('/')
        self.auth = auth
        self.api_version = api_version
        self.kwargs = kwargs

    def authenticate(self, params: inputs.AuthenticateInput, **kwargs):
        """
        认证获取 Token
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

    def server_detail(self, params: inputs.ServerDetailInput, **kwargs):
        """
        :return:
            outputs.ServerDetailOutput()
        """
        raise NotImplementedError('`server_detail()` must be implemented.')

    def server_rebuild(self, params: inputs.ServerRebuildInput, **kwargs):
        """
        重建（更换系统镜像）虚拟服务器
        :return:
            outputs.ServerRebuildOutput()
        """
        raise NotImplementedError('`server_rebuild()` must be implemented.')

    def list_images(self, params: inputs.ListImageInput, **kwargs):
        """
        列举镜像
        :return:
            output.ListImageOutput()
        """
        raise NotImplementedError('`list_images()` must be implemented.')

    def list_networks(self, params: inputs.ListNetworkInput, **kwargs):
        """
        列举子网
        :return:
            outputs.ListNetworkOutput()
        """
        raise NotImplementedError('`list_networks()` must be implemented.')

    def network_detail(self, params: inputs.NetworkDetailInput, **kwargs):
        """
        查询子网网络信息

        :return:
            outputs.NetworkDetailOutput()
        """
        raise NotImplementedError('`network_detail()` must be implemented.')
