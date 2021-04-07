from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, ServicePrivateQuotaManager, ServiceShareQuotaManager
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

        # 用户资源配额是否满足需求
        u_mgr = UserQuotaManager()
        user_quota = QuotaAPI.get_meet_user_quota(user=user, vcpu=vcpu, ram=ram, public_ip=public_ip,
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
    def get_meet_user_quota(user, vcpu: int, ram: int, public_ip: bool, user_quota_id: str = None):
        """
        获取满足条件的用户配额

        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: server所属的用户资源配额id
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        u_mgr = UserQuotaManager()
        if user_quota_id is not None:
            quota = u_mgr.get_quota_by_id(user_quota_id)
            if not quota:
                raise errors.QuotaError(_('未找到指定的用户资源配额'))

            if public_ip is True:
                u_mgr.requires(quota, vcpus=vcpu, ram=ram, public_ip=1)
            else:
                u_mgr.requires(quota, vcpus=vcpu, ram=ram, private_ip=1)

            return quota
        else:
            user_quota_qs = u_mgr.get_quota_queryset(user=user)
            u_quotas = list(user_quota_qs)

            for uq in u_quotas:
                try:
                    if public_ip is True:
                        u_mgr.requires(uq, vcpus=vcpu, ram=ram, public_ip=1)
                    else:
                        u_mgr.requires(uq, vcpus=vcpu, ram=ram, private_ip=1)
                except errors.QuotaError as e:
                    continue

                return uq

            raise errors.QuotaShortageError(_('没有可用的资源配额'))
