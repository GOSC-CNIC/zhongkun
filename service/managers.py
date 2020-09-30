from django.db import transaction
from django.utils.translation import gettext as _

from api.exceptions import APIException
from .models import UserQuota, DataCenterPrivateQuota, DataCenterShareQuota


class QuotaError(APIException):
    pass


class UserQuotaManager:
    """
    用户资源配额管理
    """
    MODEL = UserQuota

    def _create_quota(self, user):
        quota = self.MODEL(user=user)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_quota(self, user):
        """
        获取用户资源配额
        :param user:
        :return:
            UserQuota() or None
        """
        quota = self.MODEL.objects.filter(user=user).first()
        if not quota:
            quota = self._create_quota(user=user)

        return quota

    def deduct(self, user, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0):
        """
        扣除资源

        :param user: 用户对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 共有ip数
        :return:
            True

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0:
            raise QuotaError(_('参数无效，扣除资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(user=user).first()
            if not quota:
                quota = self._create_quota(user=user)
                if not quota:
                    raise QuotaError(message=_('添加用户资源配额失败'))

                quota = self.MODEL.objects.select_for_update().filter(user=user).first()

            if vcpus > 0:
                if (quota.vcpu_total - quota.vcpu_used) > vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise QuotaError(message=_('vcpu资源配额不足'))

            if ram > 0:
                if (quota.ram_total - quota.ram_used) > ram:
                    quota.ram_used = quota.ram_used + ram
                    update_fields.append('ram_used')
                else:
                    raise QuotaError(message=_('ram资源配额不足'))

            if disk_size > 0:
                if (quota.disk_size_total - quota.disk_size_used) > disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise QuotaError(message=_('硬盘资源配额不足'))

            if public_ip > 0:
                if (quota.public_ip_total - quota.public_ip_used) > public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise QuotaError(message=_('公网IP资源配额不足'))

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise QuotaError(message=_('扣除资源配额失败'))

        return True

    def increase(self, user, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0):
        """
        增加资源

        :param user: 用户对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 共有ip数
        :return:
            True

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0:
            raise QuotaError(_('参数无效，增加资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = UserQuota.objects.select_for_update().filter(user=user).first()
            if not quota:
                quota = self._create_quota(user=user)
                if not quota:
                    raise QuotaError(message=_('添加用户资源配额失败'))

                quota = UserQuota.objects.select_for_update().filter(user=user).first()

            if vcpus > 0:
                quota.vcpu_total = quota.vcpu_total + vcpus
                update_fields.append('vcpu_total')

            if ram > 0:
                quota.ram_total = quota.ram_total + ram
                update_fields.append('ram_total')

            if disk_size > 0:
                quota.disk_size_total = quota.disk_size_total + disk_size
                update_fields.append('disk_size_total')

            if public_ip > 0:
                quota.public_ip_total = quota.public_ip_total + public_ip
                update_fields.append('public_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise QuotaError(message=_('增加资源配额失败'))

        return True


class DataCenterPrivateQuotaManager:
    """
    数据中心私有资源配额管理
    """
    MODEL = DataCenterPrivateQuota

    def _create_quota(self, center):
        quota = self.MODEL(data_center=center)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_quota(self, center):
        """
        获取服务私有资源配额
        :param center: 数据中心
        :return:
            ServiceQuota() or None
        """
        quota = self.MODEL.objects.filter(data_center=center).first()
        if not quota:
            quota = self._create_quota(center=center)

        return quota

    def deduct(self, center, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0):
        """
        扣除资源

        :param center: 数据中心对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 共有ip数
        :return:
            True

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0:
            raise QuotaError(_('参数无效，扣除资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()
            if not quota:
                quota = self._create_quota(center=center)
                if not quota:
                    raise QuotaError(message=_('添加用户资源配额失败'))

                quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()

            if vcpus > 0:
                if (quota.vcpu_total - quota.vcpu_used) > vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise QuotaError(message=_('vcpu资源配额不足'))

            if ram > 0:
                if (quota.ram_total - quota.ram_used) > ram:
                    quota.ram_used = quota.ram_used + ram
                    update_fields.append('ram_used')
                else:
                    raise QuotaError(message=_('ram资源配额不足'))

            if disk_size > 0:
                if (quota.disk_size_total - quota.disk_size_used) > disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise QuotaError(message=_('硬盘资源配额不足'))

            if public_ip > 0:
                if (quota.public_ip_total - quota.public_ip_used) > public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise QuotaError(message=_('公网IP资源配额不足'))

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise QuotaError(message=_('扣除资源配额失败'))

        return True


class DataCenterShareQuotaManager:
    """
    数据中心分享资源配额管理
    """
    MODEL = DataCenterShareQuota

    def _create_quota(self, center):
        quota = self.MODEL(data_center=center)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_quota(self, center):
        """
        获取服务私有资源配额
        :param center: 数据中心
        :return:
            ServiceQuota() or None
        """
        quota = self.MODEL.objects.filter(data_center=center).first()
        if not quota:
            quota = self._create_quota(center=center)

        return quota

    def deduct(self, center, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0):
        """
        扣除资源

        :param center: 数据中心对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 共有ip数
        :return:
            True

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0:
            raise QuotaError(_('参数无效，扣除资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()
            if not quota:
                quota = self._create_quota(center=center)
                if not quota:
                    raise QuotaError(message=_('添加用户资源配额失败'))

                quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()

            if vcpus > 0:
                if (quota.vcpu_total - quota.vcpu_used) > vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise QuotaError(message=_('vcpu资源配额不足'))

            if ram > 0:
                if (quota.ram_total - quota.ram_used) > ram:
                    quota.ram_used = quota.ram_used + ram
                    update_fields.append('ram_used')
                else:
                    raise QuotaError(message=_('ram资源配额不足'))

            if disk_size > 0:
                if (quota.disk_size_total - quota.disk_size_used) > disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise QuotaError(message=_('硬盘资源配额不足'))

            if public_ip > 0:
                if (quota.public_ip_total - quota.public_ip_used) > public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise QuotaError(message=_('公网IP资源配额不足'))

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise QuotaError(message=_('扣除资源配额失败'))

        return True

    def increase(self, center, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0):
        """
        增加资源

        :param center: 数据中心对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 共有ip数
        :return:
            True

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0:
            raise QuotaError(_('参数无效，增加资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()
            if not quota:
                quota = self._create_quota(center=center)
                if not quota:
                    raise QuotaError(message=_('添加用户资源配额失败'))

                quota = self.MODEL.objects.select_for_update().filter(data_center=center).first()

            if vcpus > 0:
                quota.vcpu_total = quota.vcpu_total + vcpus
                update_fields.append('vcpu_total')

            if ram > 0:
                quota.ram_total = quota.ram_total + ram
                update_fields.append('ram_total')

            if disk_size > 0:
                quota.disk_size_total = quota.disk_size_total + disk_size
                update_fields.append('disk_size_total')

            if public_ip > 0:
                quota.public_ip_total = quota.public_ip_total + public_ip
                update_fields.append('public_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise QuotaError(message=_('增加资源配额失败'))

        return True
