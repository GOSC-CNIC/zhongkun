from datetime import datetime, timedelta

from django.db import transaction
from django.utils.translation import gettext_lazy, gettext as _
from django.db.models import Q, Subquery
from django.utils import timezone
from django.core.cache import cache

from core import errors
from api import exceptions
from .models import (UserQuota, ServicePrivateQuota, ServiceShareQuota,
                     ServiceConfig, ApplyVmService, DataCenter, ApplyDataCenter)


class UserQuotaManager:
    """
    用户资源配额管理
    """
    MODEL = UserQuota

    def create_quota(self, user, service, tag: int = None, expire_time=None):
        if tag is None:
            tag = self.MODEL.TAG_BASE

        expiration_time = expire_time if isinstance(expire_time, datetime) else (timezone.now() + timedelta(days=15))
        quota = self.MODEL(user=user, service=service, tag=tag, expiration_time=expiration_time)
        try:
            quota.save()
        except Exception as e:
            return None

        return quota

    def get_user_quota_by_id(self, _id: str, user):
        """
        查询指定用户的配额

        :param _id: 配额id
        :param user: 用户实例
        :return:
            UserQuota()

        :raises: QuotaError
        """
        quota = self.get_quota_by_id(_id)
        if not quota:
            raise errors.QuotaError.from_error(
                exceptions.NotFound(message='资源配额不存在'))

        if quota.user_id != user.id:
            raise errors.QuotaError.from_error(
                exceptions.AccessDenied(message=_('无权访问此资源配额')))

        return quota

    def delete_quota_soft(self, _id: str, user):
        """
        软删除用户的配额

        :retrun:
            None                # success
            raise QuotaError    # failed

        :raises: QuotaError
        """
        quota = self.get_user_quota_by_id(_id=_id, user=user)
        quota.deleted = True
        try:
            quota.save(update_fields=['deleted'])
        except Exception as e:
            raise errors.QuotaError.from_error(e)

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
            queryset = queryset.filter(Q(expiration_time__isnull=True) | Q(expiration_time__gt=now))

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

    def get_user_private_queryset(self, user):
        """
        用户可访问的服务私有资源配额
        """
        sq = Subquery(user.service_set.all().values_list('id', flat=True))
        return self.MODEL.objects.filter(service__in=sq).all()


class ServiceShareQuotaManager(ServiceQuotaManagerBase):
    """
    接入服务的共享资源配额管理
    """
    MODEL = ServiceShareQuota
    ERROR_MSG_PREFIX = gettext_lazy('服务的共享资源配额')


class ServiceManager:
    @staticmethod
    def filter_service(center_id: str, user=None):
        """
        :param center_id: 联邦成员机构id
        :param user: 用户对象，筛选用户有可用资源配额的服务
        """
        if center_id:
            queryset = ServiceConfig.objects.select_related('data_center').filter(
                data_center=center_id, status=ServiceConfig.Status.ENABLE)
        else:
            queryset = ServiceConfig.objects.select_related('data_center').filter(
                status=ServiceConfig.Status.ENABLE)

        if user:
            user_quotas = UserQuotaManager().filter_quota_queryset(user=user, usable=True)
            queryset = queryset.filter(id__in=Subquery(
                user_quotas.values_list('service_id', flat=True)))

        return queryset

    @staticmethod
    def get_has_perm_service(user):
        """
        用户有权限管理的服务
        """
        return user.service_set.select_related('data_center').filter(
            status=ServiceConfig.Status.ENABLE).all()

    @staticmethod
    def get_service_id_map(use_cache=False, cache_secends=60):
        """
        service id为key, service 实例为value的字典

        :param use_cache: True: 使用缓存方式；默认不使用，实时查询数据库
        :param cache_secends: 缓存时间秒
        """
        service_id_map = None
        caches_key = 'service_id_map'
        if use_cache:
            service_id_map = cache.get(caches_key)

        if service_id_map is None:
            services = ServiceConfig.objects.select_related('data_center').all()
            service_id_map = {}
            for s in services:
                service_id_map[s.id] = s

            if use_cache:
                cache.set(caches_key, service_id_map, timeout=cache_secends)

        return service_id_map


class VmServiceApplyManager:
    model = ApplyVmService

    @staticmethod
    def get_apply_queryset():
        return ApplyVmService.objects.all()

    def get_not_delete_apply_queryset(self, user=None):
        filters = {
            'deleted': False
        }
        if user:
            filters['user'] = user

        qs = self.get_apply_queryset()
        return qs.filter(**filters)

    @staticmethod
    def create_apply(data: dict, user):
        """
        创建一个服务接入申请

        :param data: dict, ApplyVmServiceSerializer.validated_data
        :param user:
        :return:
            ApplyVmService()

        :raises: Error
        """
        apply_service = ApplyVmService()
        data_center_id = data.get('data_center_id')
        center_apply_id = data.get('center_apply_id')
        if data_center_id and center_apply_id:
            raise errors.DoNotKnowWhichCenterBelongToError()

        if data_center_id:
            center = DataCenter.objects.filter(id=data_center_id).first()
            if center is None:
                raise exceptions.DataCenterNotExists()

            apply_service.data_center_id = data_center_id
        elif center_apply_id:
            center_apply = ApplyDataCenter.objects.filter(id=center_apply_id).first()
            if center_apply is None:
                raise exceptions.DataCenterApplyNotExists

            apply_service.center_apply_id = center_apply_id
        else:
            raise errors.NoCenterBelongToError()

        service_type = data.get('service_type')
        if service_type not in apply_service.ServiceType.values:
            raise exceptions.BadRequest(message='service_type值无效')

        apply_service.user = user
        apply_service.service_type = service_type
        apply_service.name = data.get('name')
        apply_service.endpoint_url = data.get('endpoint_url')
        apply_service.region = data.get('region', '')
        apply_service.api_version = data.get('api_version', '')
        apply_service.username = data.get('username', '')
        apply_service.set_password(data.get('password', ''))
        apply_service.project_name = data.get('project_name', '')
        apply_service.project_domain_name = data.get('project_domain_name', '')
        apply_service.user_domain_name = data.get('user_domain_name', '')
        apply_service.remarks = data.get('remarks', '')
        apply_service.need_vpn = data.get('need_vpn')
        apply_service.vpn_endpoint_url = data.get('vpn_endpoint_url', '')
        apply_service.vpn_api_version = data.get('vpn_api_version', '')
        apply_service.vpn_username = data.get('vpn_username', '')
        apply_service.vpn_password = data.get('vpn_password', '')
        apply_service.longitude = data.get('longitude', 0)
        apply_service.latitude = data.get('latitude', 0)
        apply_service.contact_person = data.get('contact_person', '')
        apply_service.contact_email = data.get('contact_email', '')
        apply_service.contact_telephone = data.get('contact_telephone', '')
        apply_service.contact_fixed_phone = data.get('contact_fixed_phone', '')
        apply_service.contact_address = data.get('contact_address', '')

        try:
            apply_service.save()
        except Exception as e:
            raise errors.Error.from_error(e)

        return apply_service


