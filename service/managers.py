from django.db import transaction
from django.utils.translation import gettext_lazy, gettext as _
from django.db.models import Q
from django.utils import timezone

from core import errors
from .models import UserQuota, ServicePrivateQuota, ServiceShareQuota


class UserQuotaManager:
    """
    用户资源配额管理
    """
    MODEL = UserQuota

    def _create_quota(self, user, service, tag: int = None, expire_time=None):
        if tag is None:
            tag = self.MODEL.TAG_BASE

        expiration_time = None
        if tag != self.MODEL.TAG_BASE:
            expiration_time = expire_time

        quota = self.MODEL(user=user, service=service, tag=tag, expiration_time=expiration_time)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_quota_queryset(self, user):
        """
        获取用户资源配额查询集

        :param user: 用户对象
        :return: QuerySet()
        """
        return self.MODEL.objects.filter(user=user, deleted=False).all()

    def get_base_quota_queryset(self, user):
        """
        获取用户基本资源配额查询集

        :param user:用户对象
        :return: QuerySet()
        """
        return self.get_quota_queryset(user=user).filter(tag=self.MODEL.TAG_BASE).all()

    def get_quota_by_id(self, quota_id: str):
        """
        :param quota_id: 配额id
        :return:
            UserQuota() or None
        """
        return self.MODEL.objects.filter(id=quota_id).first()

    def deduct(self, user, quota_id: str, vcpus: int = 0, ram: int = 0,
               disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        扣除(已用)资源

        :param user: 用户对象
        :param quota_id: 配额id
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError, QuotaShortageError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，扣除资源配额不得小于0'))

        if not user.id:
            raise errors.QuotaError(_('参数无效，无效的未知用户'))

        if not quota_id:
            raise errors.QuotaError(_('参数无效，无效的资源配额id'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id, user=user).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))

            if quota.is_expire_now():
                raise errors.QuotaShortageError(message=_('您的资源配额已过期'))

            if vcpus > 0:
                if (quota.vcpu_total - quota.vcpu_used) >= vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise errors.QuotaShortageError(message=_('您的vCPU资源配额不足'))

            if ram > 0:
                if (quota.ram_total - quota.ram_used) >= ram:
                    quota.ram_used = quota.ram_used + ram
                    update_fields.append('ram_used')
                else:
                    raise errors.QuotaShortageError(message=_('您的Ram资源配额不足'))

            if disk_size > 0:
                if (quota.disk_size_total - quota.disk_size_used) >= disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise errors.QuotaShortageError(message=_('您的硬盘资源配额不足'))

            if public_ip > 0:
                if (quota.public_ip_total - quota.public_ip_used) >= public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise errors.QuotaShortageError(message=_('您的公网IP资源配额不足'))

            if private_ip > 0:
                if (quota.private_ip_total - quota.private_ip_used) >= private_ip:
                    quota.private_ip_used = quota.private_ip_used + private_ip
                    update_fields.append('private_ip_used')
                else:
                    raise errors.QuotaShortageError(message=_('您的私网IP资源配额不足'))

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=_('扣除资源配额失败'))

        return quota

    def release(self, user, quota_id: str, vcpus: int = 0, ram: int = 0,
                disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        释放(已用)资源

        :param user: 用户对象
        :param quota_id: 配额id
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError, QuotaShortageError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，释放资源配额不得小于0'))

        if not user.id:
            raise errors.QuotaError(_('参数无效，无效的未知用户'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id, user=user).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))

            if vcpus > 0:
                quota.vcpu_used = max(quota.vcpu_used - vcpus, 0)
                update_fields.append('vcpu_used')

            if ram > 0:
                quota.ram_used = max(quota.ram_used - ram, 0)
                update_fields.append('ram_used')

            if disk_size > 0:
                quota.disk_size_used = max(quota.disk_size_used - disk_size, 0)
                update_fields.append('disk_size_used')

            if public_ip > 0:
                quota.public_ip_used = max(quota.public_ip_used - public_ip, 0)
                update_fields.append('public_ip_used')

            if private_ip > 0:
                quota.private_ip_used = max(quota.private_ip_used - private_ip, 0)
                update_fields.append('private_ip_used')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=_('释放资源配额失败'))

        return quota

    def increase(self, user, quota_id: str, vcpus: int = 0, ram: int = 0,
                 disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        增加资源总配额

        :param user: 用户对象
        :param quota_id: 配额id
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，增加资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id, user=user).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))

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

            if private_ip > 0:
                quota.private_ip_total = quota.private_ip_total + private_ip
                update_fields.append('private_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=_('增加资源配额失败'))

        return quota

    def decrease(self, user, quota_id: str, vcpus: int = 0, ram: int = 0,
                 disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        减少资源总配额

        :param user: 用户对象
        :param quota_id: 配额id
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，减少资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id, user=user).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))

            if vcpus > 0:
                quota.vcpu_total = max(quota.vcpu_total - vcpus, 0)
                update_fields.append('vcpu_total')

            if ram > 0:
                quota.ram_total = max(quota.ram_total - ram, 0)
                update_fields.append('ram_total')

            if disk_size > 0:
                quota.disk_size_total = max(quota.disk_size_total - disk_size, 0)
                update_fields.append('disk_size_total')

            if public_ip > 0:
                quota.public_ip_total = max(quota.public_ip_total - public_ip, 0)
                update_fields.append('public_ip_total')

            if private_ip > 0:
                quota.private_ip_total = max(quota.private_ip_total - private_ip, 0)
                update_fields.append('private_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=_('减少资源配额失败'))

        return quota

    @staticmethod
    def requires(quota, vcpus: int = 0, ram: int = 0, disk_size: int = 0,
                 public_ip: int = 0, private_ip: int = 0):
        """
        是否满足资源需求

        :param quota: 数据中心资源配额对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            True

        :raises: QuotaError, QuotaShortageError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，扣除资源配额不得小于0'))

        if quota.is_expire_now():
            raise errors.QuotaShortageError(message=_('您的资源配额已过期'))

        if vcpus > 0 and (quota.vcpu_total - quota.vcpu_used) < vcpus:
            raise errors.QuotaShortageError(_('您的vCPU资源配额不足'))

        if ram > 0 and (quota.ram_total - quota.ram_used) < ram:
            raise errors.QuotaShortageError(_('您的Ram资源配额不足'))

        if disk_size > 0 and (quota.disk_size_total - quota.disk_size_used) < disk_size:
            raise errors.QuotaShortageError(_('您的Disk资源配额不足'))

        if public_ip > 0 and (quota.public_ip_total - quota.public_ip_used) < public_ip:
            raise errors.QuotaShortageError(_('您的公网IP资源配额不足'))

        if private_ip > 0 and (quota.private_ip_total - quota.private_ip_used) < private_ip:
            raise errors.QuotaShortageError(_('您的私网IP资源配额不足'))

        return True

    def filter_quota_queryset(self, user, service=None, usable=None):
        """
        过滤用户资源配额查询集

        :param user:
        :param service: 服务对象，暂时预留
        :param usable: 是否过滤可用的(未过有效期的)
        :return:
        """
        queryset = self.get_quota_queryset(user=user)
        if service:
            queryset = queryset.filter(service=service)

        if usable:
            now = timezone.now()
            queryset = queryset.filter(Q(tag=UserQuota.TAG_BASE) | (
                    Q(tag=UserQuota.TAG_PROBATION) & Q(expiration_time__gt=now)))

        return queryset.order_by('id')


class ServiceQuotaManagerBase:
    """
    服务资源配额管理基类
    """
    MODEL = None
    ERROR_MSG_PREFIX = gettext_lazy('服务')

    def _prefix_msg(self, msg: str):
        return self.ERROR_MSG_PREFIX + ',' + msg

    def _create_quota(self, service):
        quota = self.MODEL(service=service)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_quota(self, service):
        """
        获取服务资源配额
        :param service: 接入服务配置
        :return:
            self.MODEL() or None
        """
        quota = self.MODEL.objects.filter(service=service).first()
        if not quota:
            quota = self._create_quota(service=service)

        return quota

    def deduct(self, service, vcpus: int = 0, ram: int = 0, disk_size: int = 0,
               public_ip: int = 0, private_ip: int = 0):
        """
        扣除资源

        :param service: 接入服务
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，扣除资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(service=service).first()
            if not quota:
                quota = self._create_quota(service=service)
                if not quota:
                    raise errors.QuotaError(message=self._prefix_msg(_('创建资源配额失败')))

                quota = self.MODEL.objects.select_for_update().filter(service=service).first()

            if vcpus > 0:
                if (quota.vcpu_total - quota.vcpu_used) >= vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('vCPU资源配额不足')))

            if ram > 0:
                if (quota.ram_total - quota.ram_used) >= ram:
                    quota.ram_used = quota.ram_used + ram
                    update_fields.append('ram_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('Ram资源配额不足')))

            if disk_size > 0:
                if (quota.disk_size_total - quota.disk_size_used) >= disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('硬盘资源配额不足')))

            if public_ip > 0:
                if (quota.public_ip_total - quota.public_ip_used) >= public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('公网IP资源配额不足')))

            if private_ip > 0:
                if (quota.private_ip_total - quota.private_ip_used) >= private_ip:
                    quota.private_ip_used = quota.private_ip_used + private_ip
                    update_fields.append('private_ip_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('私网IP资源配额不足')))

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=self._prefix_msg(_('扣除资源配额失败')))

        return quota

    def release(self, service, vcpus: int = 0, ram: int = 0, disk_size: int = 0,
                public_ip: int = 0, private_ip: int = 0):
        """
        释放已用的资源

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，释放资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(service=service).first()
            if not quota:
                quota = self._create_quota(service=service)
                if not quota:
                    raise errors.QuotaError(message=self._prefix_msg(_('创建资源配额失败')))

                quota = self.MODEL.objects.select_for_update().filter(service=service).first()

            if vcpus > 0:
                quota.vcpu_used = max(quota.vcpu_used - vcpus, 0)
                update_fields.append('vcpu_used')

            if ram > 0:
                quota.ram_used = max(quota.ram_used - ram, 0)
                update_fields.append('ram_used')

            if disk_size > 0:
                quota.disk_size_used = max(quota.disk_size_used - disk_size, 0)
                update_fields.append('disk_size_used')

            if public_ip > 0:
                quota.public_ip_used = max(quota.public_ip_used - public_ip, 0)
                update_fields.append('public_ip_used')

            if private_ip > 0:
                quota.private_ip_used = max(quota.private_ip_used - private_ip, 0)
                update_fields.append('private_ip_used')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=self._prefix_msg(_('释放资源配额失败')))

        return quota

    def increase(self, service, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        增加总资源配额

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，增加资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(service=service).first()
            if not quota:
                quota = self._create_quota(service=service)
                if not quota:
                    raise errors.QuotaError(message=self._prefix_msg(_('创建资源配额失败')))

                quota = self.MODEL.objects.select_for_update().filter(service=service).first()

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

            if private_ip > 0:
                quota.private_ip_total = quota.private_ip_total + private_ip
                update_fields.append('private_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=self._prefix_msg(_('增加资源配额失败')))

        return quota

    def decrease(self, service, vcpus: int = 0, ram: int = 0, disk_size: int = 0, public_ip: int = 0, private_ip: int = 0):
        """
        减少资源总配额

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，增加资源配额不得小于0'))

        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(service=service).first()
            if not quota:
                quota = self._create_quota(service=service)
                if not quota:
                    raise errors.QuotaError(message=self._prefix_msg(_('创建资源配额失败')))

                quota = self.MODEL.objects.select_for_update().filter(service=service).first()

            if vcpus > 0:
                quota.vcpu_total = max(quota.vcpu_total - vcpus, 0)
                update_fields.append('vcpu_total')

            if ram > 0:
                quota.ram_total = max(quota.ram_total - ram, 0)
                update_fields.append('ram_total')

            if disk_size > 0:
                quota.disk_size_total = max(quota.disk_size_total - disk_size, 0)
                update_fields.append('disk_size_total')

            if public_ip > 0:
                quota.public_ip_total = max(quota.public_ip_total - public_ip, 0)
                update_fields.append('public_ip_total')

            if private_ip > 0:
                quota.private_ip_total = max(quota.private_ip_total - private_ip, 0)
                update_fields.append('private_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=self._prefix_msg(_('增加资源配额失败')))

        return quota

    def requires(self, quota, vcpus: int = 0, ram: int = 0, disk_size: int = 0,
                 public_ip: int = 0, private_ip: int = 0):
        """
        是否满足资源需求

        :param quota: 数据中心资源配额对象
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            True
            False

        :raises: QuotaError, QuotaShortageError
        """
        if vcpus < 0 or ram < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，扣除资源配额不得小于0'))

        if vcpus > 0 and (quota.vcpu_total - quota.vcpu_used) < vcpus:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("vCPU资源配额不足")))

        if ram > 0 and (quota.ram_total - quota.ram_used) < ram:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("Ram资源配额不足")))

        if disk_size > 0 and (quota.disk_size_total - quota.disk_size_used) < disk_size:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("Disk资源配额不足")))

        if public_ip > 0 and (quota.public_ip_total - quota.public_ip_used) < public_ip:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("公网IP资源配额不足")))

        if private_ip > 0 and (quota.private_ip_total - quota.private_ip_used) < private_ip:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("私网IP资源配额不足")))

        return True


class ServicePrivateQuotaManager(ServiceQuotaManagerBase):
    """
    接入服务的私有资源配额管理
    """
    MODEL = ServicePrivateQuota
    ERROR_MSG_PREFIX = gettext_lazy('服务的私有资源配额')


class ServiceShareQuotaManager(ServiceQuotaManagerBase):
    """
    接入服务的共享资源配额管理
    """
    MODEL = ServiceShareQuota
    ERROR_MSG_PREFIX = gettext_lazy('服务的共享资源配额')
