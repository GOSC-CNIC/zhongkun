from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, DataCenterPrivateQuotaManager, DataCenterShareQuotaManager
from . import errors
from service.models import DataCenter


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(data_center: DataCenter, user, vcpu: int, ram: int, public_ip: bool,
                                  user_quota_id: int = None):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.数据中心管理员优先使用数据中心的私有资源配额，不扣除用户资源配额；
            2.普通用户，只能使用各数据中心的共享资源配额，并扣除用户资源配额

        :param data_center: 数据中心
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param user_quota_id: 指定要使用的用户资源配额id，默认不指定
        :return:
            (
                bool,               # True:使用的共享资源配额; False使用的私有资源配额
                user_quota          # 使用的用户配额对象；None(未使用)
            )

        :raises: QuotaShortageError, QuotaError
        """
        # 用户是数据中心管理员，优化使用数据中心私有资源
        pri_mgr = DataCenterPrivateQuotaManager()
        pri_center_quota = pri_mgr.get_quota(center=data_center)
        use_shared_quota = True  # 标记使用数据中心分享配额或私有配额
        if data_center.users.filter(id=user.id).exists():
            try:
                if public_ip is True:
                    pri_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, public_ip=1)
                else:
                    pri_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, private_ip=1)

                use_shared_quota = False  # 使用私有配额
            except errors.QuotaError as e:
                pass

        # 资源配额满足要求，扣除数据中心资源或用户资源
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        u_mgr = UserQuotaManager()
        share_mgr = DataCenterShareQuotaManager()
        # 使用共享资源时，需检测用户资源配额和数据中心共享资源配额是否满足需求
        user_quota = None
        if use_shared_quota:
            user_quota = QuotaAPI.get_meet_user_quota(user=user, vcpu=vcpu, ram=ram, public_ip=public_ip,
                                                      user_quota_id=user_quota_id)

            # 使用共享资源配额
            shared_center_quota = share_mgr.get_quota(center=data_center)
            if public_ip is True:
                share_mgr.requires(shared_center_quota, vcpus=vcpu, ram=ram, public_ip=1)
            else:
                share_mgr.requires(shared_center_quota, vcpus=vcpu, ram=ram, private_ip=1)

            u_mgr.deduct(user=user, quota_id=user_quota.id, vcpus=vcpu, ram=ram, **kwargs)
            try:
                share_mgr.deduct(center=data_center, vcpus=vcpu, ram=ram, **kwargs)
            except errors.QuotaError as e:
                u_mgr.release(user=user, vcpus=vcpu, ram=ram, **kwargs)
                raise e
        else:
            pri_mgr.deduct(center=data_center, vcpus=vcpu, ram=ram, **kwargs)

        return use_shared_quota, user_quota

    @staticmethod
    def server_quota_release(data_center: DataCenter, user, vcpu: int, ram: int, public_ip: bool,
                             use_shared_quota: bool, user_quota_id: int):
        """
        释放服务器占用的资源配额

        原则：
            服务器使用的是数据中心的私有资源配额，与用户资源配额无关；

        :param data_center: 数据中心
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
            try:
                u_mgr.release(user=user, quota_id=user_quota_id, vcpus=vcpu, ram=ram, **kwargs)
            except errors.QuotaError as e:
                pass
            DataCenterShareQuotaManager().release(center=data_center, vcpus=vcpu, ram=ram, **kwargs)
        else:
            DataCenterPrivateQuotaManager().release(center=data_center, vcpus=vcpu, ram=ram, **kwargs)

    @staticmethod
    def get_meet_user_quota(user, vcpu: int, ram: int, public_ip: bool, user_quota_id: int = None):
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
            if not isinstance(user_quota_id, int) or user_quota_id <= 0:
                raise errors.QuotaError(_('无效的用户资源配额id'))

            quota = u_mgr.get_quota_by_id(user_quota_id)
            if not quota:
                raise errors.QuotaError(_('未找到指定的用户资源配额'))

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
