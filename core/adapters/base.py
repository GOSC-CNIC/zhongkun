"""

"""
from . import inputs
from . import outputs


class BaseAdapter:
    """
    不同类型的服务平台的api适配器的基类
    """
    adapter_name = 'adapter'
    SYSTEM_DISK_MIN_SIZE_GB = 50        # 系统盘最小尺寸，单位GiB

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

    def image_detail(self, params: inputs.ImageDetailInput, **kwargs):
        """
        查询镜像信息
        :return:
            output.ImageDetailOutput()
        """
        raise NotImplementedError('`image_detail()` must be implemented.')

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

    def list_availability_zones(self, params: inputs.ListAvailabilityZoneInput):
        """
        列举可用区
        :return:
            outputs.ListAvailabilityZoneOutput()
        """
        raise NotImplementedError('`list_availability_zones()` must be implemented.')

    def disk_create(self, params: inputs.DiskCreateInput):
        """
        创建云硬盘
        :return:
            outputs.DiskCreateOutput()
        """
        raise NotImplementedError('`disk_create()` must be implemented.')

    def disk_create_pretend(self, params: inputs.DiskCreateInput):
        """
        检查是否满足云硬盘的创建条件，是否有足够资源、其他什么限制等等

        * 适配器子类实现此方法，被视为不支持云硬盘功能
        * 适配器子类必须继承实现此方法（即使什么都不检查），根据各自服务平台尽可能确认是否满足创建云硬盘的条件

        :return:
            outputs.DiskCreatePretendOutput()
        """
        raise NotImplementedError('`disk_create_pretend()` must be implemented.')

    def disk_delete(self, params: inputs.DiskDeleteInput):
        """
        删除云硬盘
        :return:
            outputs.DiskDeleteOutput()
        """
        raise NotImplementedError('`disk_delete()` must be implemented.')

    def disk_attach(self, params: inputs.DiskAttachInput):
        """
        云硬盘挂载到云主机
        :return:
            outputs.DiskAttachOutput()
        """
        raise NotImplementedError('`disk_attach()` must be implemented.')

    def disk_detach(self, params: inputs.DiskDetachInput):
        """
        从云主机卸载云硬盘
        :return:
            outputs.DiskDetachOutput()
        """
        raise NotImplementedError('`disk_detach()` must be implemented.')

    def disk_detail(self, params: inputs.DiskDetailInput):
        """
        查询云硬盘
        :return:
            outputs.DiskDetailOutput()
        """
        raise NotImplementedError('`disk_detail()` must be implemented.')

    def get_quota(self, params: inputs.QuotaInput):
        """
        查询资源配额信息（可用总资源）

        :return:
            outputs.QuotaOutput()
        """
        raise NotImplementedError('`get_quota()` must be implemented.')

    def get_version(self):
        """
        查询服务的版本

        :return:
            outputs.VersionOutput()
        """
        raise NotImplementedError('`get_version()` must be implemented.')

    def server_snapshot_create(self, params: inputs.ServerSnapshotCreateInput) -> outputs.ServerSnapshotCreateOutput:
        """
        创建云主机快照

        :return:
            outputs.ServerSnapshotCreateOutput()
        """
        raise NotImplementedError('`server_snapshot_create()` must be implemented.')

    def server_snapshot_delete(self, params: inputs.ServerSnapshotDeleteInput) -> outputs.ServerSnapshotDeleteOutput:
        """
        删除云主机快照
        """
        raise NotImplementedError('`server_snapshot_delete()` must be implemented.')

    def server_rollback_snapshot(
            self, params: inputs.ServerRollbackSnapshotInput) -> outputs.ServerRollbackSnapshotOutput:
        """
        云主机回滚到快照
        """
        raise NotImplementedError('`server_rollback_snapshot()` must be implemented.')

    def server_owner_change(self, params: inputs.ServerOwnerChangeInput) -> outputs.ServerOwnerChangeOutput:
        """
        云主机拥有者变更，主要适用于EVCloud
        """
        raise NotImplementedError('`server_owner_change()` must be implemented.')

    def server_shared(self, params: inputs.ServerSharedInput) -> outputs.ServerSharedOutput:
        """
        云主机共享用户和权限更新替换，主要适用于EVCloud
        """
        raise NotImplementedError('`server_shared()` must be implemented.')
