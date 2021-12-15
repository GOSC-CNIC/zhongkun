from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, ServicePrivateQuotaManager
from . import errors


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(service, user, vcpu: int, ram: int, public_ip: bool,
                                  user_quota_id: str = None):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.使用服务私有资源配额，并扣除用户资源配额；

        :param service: 接入服务
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: 指定要使用的用户资源配额id，默认不指定
        :return:
            user_quota          # 用户配额对象

        :raises: QuotaShortageError, QuotaError
        """
        if not user_quota_id:
            raise errors.QuotaError.from_error(
                errors.BadRequestError('必须指定一个用户资源配额'))

        # 资源配额满足要求，扣除数据中心资源或用户资源
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        # 资源配额是否满足需求，用户是否有使用权限
        u_mgr = UserQuotaManager()
        user_quota = QuotaAPI.get_perm_meet_quota(user=user, vcpu=vcpu, ram=ram, public_ip=public_ip,
                                                  user_quota_id=user_quota_id)

        # 数据中心私有资源配额是否满足需求
        pri_mgr = ServicePrivateQuotaManager()
        pri_service_quota = pri_mgr.get_quota(service=service)
        if public_ip is True:
            pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, public_ip=1)
        else:
            pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, private_ip=1)

        # 扣除服务私有资源配额和用户配额
        pri_mgr.deduct(service=service, vcpus=vcpu, ram=ram, **kwargs)
        try:
            u_mgr.deduct(user=user, quota_id=user_quota.id, vcpus=vcpu, ram=ram, **kwargs)
        except errors.QuotaError as e:
            pri_mgr.release(service=service, vcpus=vcpu, ram=ram, **kwargs)
            raise e

        return user_quota

    @staticmethod
    def server_quota_release(service, vcpu: int, ram: int, public_ip: bool,
                             user_quota_id=None):
        """
        释放服务器占用的服务提供者的私有资源配额
        创建资源失败时，用户配额返还可通过参数user_quota_id指定，默认忽略

        :param service: 接入的服务对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: 用户配额id
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        if user_quota_id:
            try:
                UserQuotaManager().release(quota_id=user_quota_id, vcpus=vcpu, ram=ram, **kwargs)
            except errors.QuotaError as e:
                pass

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
