from django.utils.translation import gettext as _

from service.managers import UserQuotaManager, DataCenterPrivateQuotaManager, DataCenterShareQuotaManager
from . import errors
from service.models import DataCenter


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(data_center: DataCenter, user, vcpu: int, ram: int, public_ip: bool):
        """
        检测资源配额是否满足，并申请扣除

        :param data_center: 数据中心
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :return:
            True    # 使用的共享资源配额
            False   # 使用的私有资源配额

        :raises: QuotaShortageError, QuotaError
        """
        # 用户资源配额是否满足
        u_mgr = UserQuotaManager()
        user_quota = u_mgr.get_quota(user=user)
        if public_ip is True:
            u_mgr.requires(user_quota, vcpus=vcpu, ram=ram, public_ip=1)
        else:
            u_mgr.requires(user_quota, vcpus=vcpu, ram=ram, private_ip=1)

        # 用户是数据中心管理员，优化使用数据中心私有资源
        pri_mgr = DataCenterPrivateQuotaManager()
        pri_center_quota = pri_mgr.get_quota(center=data_center)
        use_shared_quota = True     # 标记使用数据中心分享配额或私有配额
        if user in data_center.users:
            try:
                if public_ip is True:
                    pri_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, public_ip=1)
                else:
                    pri_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, private_ip=1)

                use_shared_quota = False    # 使用私有配额
            except errors.QuotaError as e:
                pass

        share_mgr = DataCenterShareQuotaManager()
        if use_shared_quota:    # 使用共享资源配额
            if public_ip is True:
                share_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, public_ip=1)
            else:
                share_mgr.requires(pri_center_quota, vcpus=vcpu, ram=ram, private_ip=1)

        # 资源配额满足要求，扣除用户资源和数据中心资源
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        u_mgr.deduct(user=user, vcpus=vcpu, ram=ram, **kwargs)
        try:
            if use_shared_quota:
                share_mgr.deduct(center=data_center, vcpus=vcpu, ram=ram, **kwargs)
            else:
                pri_mgr.deduct(center=data_center, vcpus=vcpu, ram=ram, **kwargs)
        except errors.QuotaError as e:
            u_mgr.release(user=user, vcpus=vcpu, ram=ram, **kwargs)
            raise e

        return use_shared_quota

    @staticmethod
    def server_quota_release(data_center: DataCenter, user, vcpu: int, ram: int, public_ip: bool, use_shared_quota: bool):
        """
        释放服务器占用的资源配额

        :param data_center: 数据中心
        :param user: 用户对象
        :param vcpu: vCPU数
        :param ram: 内存大小, 单位Mb
        :param public_ip: True(公网IP); False(私网IP)
        :param use_shared_quota：True(共享资源配额); False(私有资源配额)
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        u_mgr = UserQuotaManager()
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        u_mgr.release(user=user, vcpus=vcpu, ram=ram, **kwargs)
        if use_shared_quota:
            DataCenterShareQuotaManager().release(center=data_center, vcpus=vcpu, ram=ram, **kwargs)
        else:
            DataCenterPrivateQuotaManager().release(center=data_center, vcpus=vcpu, ram=ram, **kwargs)


