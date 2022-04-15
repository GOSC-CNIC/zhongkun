from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, ServicePrivateQuotaManager
from . import errors


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(service, vcpu: int, ram: int, public_ip: bool):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.使用服务私有资源配额

        :param service: 接入服务
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :return:
            quota          # 服务私有配额对象

        :raises: QuotaShortageError, QuotaError
        """
        # 资源配额满足要求，扣除数据中心资源或用户资源
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        # 扣除服务私有资源配额和用户配额
        pri_quota = ServicePrivateQuotaManager().deduct(service=service, vcpus=vcpu, ram=ram, **kwargs)
        return pri_quota

    @staticmethod
    def server_quota_release(service, vcpu: int, ram: int, public_ip: bool):
        """
        释放服务器占用的服务提供者的私有资源配额

        :param service: 接入的服务对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        ServicePrivateQuotaManager().release(service=service, vcpus=vcpu, ram=ram, **kwargs)

    @staticmethod
    def get_perm_meet_quota(user, vcpu: int, ram: int, public_ip: bool, user_quota_id: str):
        """
        获取用户有使用权限的，并且满足条件的个人或vo组资源配额

        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: server所属的用户资源配额id
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        u_mgr = UserQuotaManager()
        try:
            quota = u_mgr.get_user_manage_perm_quota(user_quota_id, user=user)
        except errors.Error as e:
            raise errors.QuotaError.from_error(e)

        if public_ip is True:
            u_mgr.requires(quota, vcpus=vcpu, ram=ram, public_ip=1)
        else:
            u_mgr.requires(quota, vcpus=vcpu, ram=ram, private_ip=1)

        return quota

    @staticmethod
    def service_private_quota_meet(service, vcpu: int, ram: int, public_ip: bool):
        """
        检查服务私有资源配额是否满足需求

        :raises: QuotaError, QuotaShortageError
        """
        pri_mgr = ServicePrivateQuotaManager()
        pri_service_quota = pri_mgr.get_quota(service=service)
        if public_ip is True:
            pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, public_ip=1)
        else:
            pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, private_ip=1)

        return pri_service_quota
