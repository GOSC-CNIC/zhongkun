from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, ServicePrivateQuotaManager, ServiceShareQuotaManager
from . import errors


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(service, user, vcpu: int, ram: int, public_ip: bool,
                                  user_quota_id: str = None, private_quota_id: str = None):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.优先使用服务私有资源配额，不扣除用户资源配额；
            2.普通用户，只能使用各数据中心的共享资源配额，并扣除用户资源配额

        :param service: 接入服务
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: 指定要使用的用户资源配额id，默认不指定
        :param private_quota_id: 指定要使用的服务的私有资源配额id，默认不指定
        :return:
            (
                bool,               # True:使用的共享资源配额; False使用的私有资源配额
                user_quota          # 使用的用户配额对象；None(未使用)
            )

        :raises: QuotaShortageError, QuotaError
        """
        # 资源配额满足要求，扣除数据中心资源或用户资源
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        # 优化使用数据中心私有资源
        if private_quota_id:
            pri_mgr = ServicePrivateQuotaManager()
            pri_service_quota = pri_mgr.get_quota(service=service)
            if private_quota_id != private_quota_id:
                raise errors.NoSuchQuotaError(message='"private_quota_id"和指定的service服务不匹配')

            if public_ip is True:
                pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, public_ip=1)
            else:
                pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram=ram, private_ip=1)

            pri_mgr.deduct(service=service, vcpus=vcpu, ram=ram, **kwargs)
            return False, None      # 使用私有配额
        elif user_quota_id:
            u_mgr = UserQuotaManager()
            share_mgr = ServiceShareQuotaManager()
            # 使用共享资源时，需检测用户资源配额和数据中心共享资源配额是否满足需求
            user_quota = QuotaAPI.get_meet_user_quota(user=user, vcpu=vcpu, ram=ram, public_ip=public_ip,
                                                      user_quota_id=user_quota_id)

            # 使用共享资源配额
            shared_center_quota = share_mgr.get_quota(service=service)
            if public_ip is True:
                share_mgr.requires(shared_center_quota, vcpus=vcpu, ram=ram, public_ip=1)
            else:
                share_mgr.requires(shared_center_quota, vcpus=vcpu, ram=ram, private_ip=1)

            u_mgr.deduct(user=user, quota_id=user_quota.id, vcpus=vcpu, ram=ram, **kwargs)
            try:
                share_mgr.deduct(service=service, vcpus=vcpu, ram=ram, **kwargs)
            except errors.QuotaError as e:
                u_mgr.release(user=user, vcpus=vcpu, ram=ram, **kwargs)
                raise e

            return True, user_quota  # 使用数据中心分享配额
        else:
            raise errors.QuotaError.from_error(
                errors.BadRequestError('必须指定一个用户资源配额或服务私有资源配额'))

    @staticmethod
    def server_quota_release(service, user, vcpu: int, ram: int, public_ip: bool,
                             use_shared_quota: bool, user_quota_id: str):
        """
        释放服务器占用的资源配额

        原则：
            服务器使用的是接入服务的私有资源配额，与用户资源配额无关；

        :param service: 接入的服务对象
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param use_shared_quota：True(共享资源配额); False(私有资源配额)
        :param user_quota_id: server所属的用户资源配额id
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        u_mgr = UserQuotaManager()
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        if use_shared_quota:
            if user_quota_id:
                try:
                    u_mgr.release(user=user, quota_id=user_quota_id, vcpus=vcpu, ram=ram, **kwargs)
                except errors.QuotaError as e:
                    pass

            ServiceShareQuotaManager().release(service=service, vcpus=vcpu, ram=ram, **kwargs)
        else:
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
