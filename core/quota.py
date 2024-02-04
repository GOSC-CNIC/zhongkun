from servers.managers import ServicePrivateQuotaManager


class QuotaAPI:
    @staticmethod
    def server_create_quota_apply(service, vcpu: int, ram_gib: int, public_ip: bool):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.使用服务私有资源配额

        :param service: 接入服务
        :param vcpu: vCPU数
        :param ram_gib: 内存大小, 单位Gb
        :param public_ip: True(公网IP); False(私网IP)
        :return:
            quota          # 服务私有配额对象

        :raises: QuotaShortageError, QuotaError
        """
        if public_ip:
            kwargs = {'public_ip': 1}
        else:
            kwargs = {'private_ip': 1}

        pri_quota = ServicePrivateQuotaManager().deduct(service=service, vcpus=vcpu, ram_gib=ram_gib, **kwargs)
        return pri_quota

    @staticmethod
    def server_quota_release(service, vcpu: int, ram_gib: int, public_ips: int, private_ips: int):
        """
        释放服务器占用的服务提供者的私有资源配额

        :param service: 接入的服务对象
        :param vcpu: vCPU数
        :param ram_gib: 内存大小, 单位Gb
        :param public_ips: 公网ip的数量
        :param private_ips: 私网ip的数量
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        ServicePrivateQuotaManager().release(
            service=service, vcpus=vcpu, ram_gib=ram_gib, public_ip=public_ips, private_ip=private_ips)

    @staticmethod
    def service_private_quota_meet(service, vcpu: int, ram_gib: int, public_ips: int, private_ips: int):
        """
        检查服务私有资源配额是否满足需求

        :raises: QuotaError, QuotaShortageError
        """
        pri_mgr = ServicePrivateQuotaManager()
        pri_service_quota = pri_mgr.get_quota(service=service)
        pri_mgr.requires(pri_service_quota, vcpus=vcpu, ram_gib=ram_gib, public_ip=public_ips, private_ip=private_ips)
        return pri_service_quota

    @staticmethod
    def service_private_disk_quota_meet(service, disk_size: int):
        """
        检查服务单元私有资源云硬盘配额是否满足需求

        :raises: QuotaError, QuotaShortageError
        """
        pri_mgr = ServicePrivateQuotaManager()
        pri_service_quota = pri_mgr.get_quota(service=service)
        pri_mgr.requires(pri_service_quota, disk_size=disk_size)
        return pri_service_quota

    @staticmethod
    def disk_create_quota_apply(service, disk_size: int):
        """
        检测资源配额是否满足，并申请扣除

        原则：
            1.使用服务私有资源配额

        :param service: 接入服务
        :param disk_size: 容量大小, 单位Gb
        :return:
            quota          # 服务私有配额对象

        :raises: QuotaShortageError, QuotaError
        """
        return ServicePrivateQuotaManager().deduct(service=service, disk_size=disk_size)

    @staticmethod
    def disk_quota_release(service, disk_size: int):
        """
        释放云硬盘占用的服务提供者的私有资源配额

        :param service: 接入的服务对象
        :param disk_size: 大小, 单位Gb
        :return:

        :raises: QuotaShortageError, QuotaError
        """
        ServicePrivateQuotaManager().release(service=service, disk_size=disk_size)
