from datetime import datetime, timedelta

from django.db import transaction
from django.utils.translation import gettext_lazy, gettext as _
from django.db.models import Q, Subquery
from django.utils import timezone
from django.core.cache import cache

from users.models import UserProfile
from core import errors
from core.utils import test_service_ok, InvalidServiceError
from vo.managers import VoManager
from .models import (
    UserQuota, ServicePrivateQuota, ServiceShareQuota, ServiceConfig, ApplyVmService,
    DataCenter, ApplyOrganization, ApplyQuota
)


class UserQuotaManager:
    """
    用户资源配额管理
    """
    MODEL = UserQuota

    def create_quota(self, user, service, tag: int = None, expire_time=None,
                     classification=UserQuota.Classification.PERSONAL, vo_id=None):
        """
        :raises: QuotaError
        """
        if classification == UserQuota.Classification.VO and not vo_id:
            return errors.QuotaError(message=_('当参数classification为“vo”时，参数vo不能为None'))

        if tag is None:
            tag = self.MODEL.TAG_BASE

        if isinstance(expire_time, datetime):
            expiration_time = expire_time
        else:
            expiration_time = (timezone.now() + timedelta(days=UserQuota.EXPIRATION_DAYS))

        quota = self.MODEL(user=user, service=service, tag=tag, expiration_time=expiration_time,
                           classification=classification, vo_id=vo_id)
        try:
            quota.save()
        except Exception as e:
            return errors.QuotaError.from_error(e)

        return quota

    def get_user_read_perm_quota(self, _id: str, user):
        """
        查询用户有访问权限的的配额

        :param _id: 配额id
        :param user: 用户实例
        :return:
            UserQuota()

        :raises: QuotaError
        """
        quota = self.get_quota_by_id(_id)
        if not quota:
            raise errors.QuotaError.from_error(
                errors.NotFound(message='资源配额不存在'))

        if quota.classification == quota.Classification.PERSONAL:
            if not quota.user_id or quota.user_id != user.id:
                raise errors.QuotaError.from_error(
                    errors.AccessDenied(message=_('你没有权限访问此配额')))
        elif quota.classification == quota.Classification.VO:
            if quota.vo is None:
                raise errors.ConflictError(message=_('vo组信息丢失，无法判断你是否有权限访问'))

            try:
                VoManager.check_read_perm(vo=quota.vo, user=user)
            except errors.Error as exc:
                raise errors.AccessDenied.from_error(exc)

        return quota

    def get_user_manage_perm_quota(self, _id: str, user):
        """
        查询用户有管理权限的的配额

        :param _id: 配额id
        :param user: 用户实例
        :return:
            UserQuota()

        :raises: QuotaError
        """
        quota = self.get_quota_by_id(_id)
        if not quota:
            raise errors.QuotaError.from_error(
                errors.NotFound(message='资源配额不存在'))

        if quota.classification == quota.Classification.PERSONAL:
            if not quota.user_id or quota.user_id != user.id:
                raise errors.QuotaError.from_error(
                    errors.AccessDenied(message=_('你没有权限管理此配额')))
        elif quota.classification == quota.Classification.VO:
            if quota.vo is None:
                raise errors.ConflictError(message=_('vo组信息丢失，无法判断你是否有权限访问'))

            try:
                VoManager.check_manager_perm(vo=quota.vo, user=user)
            except errors.Error as exc:
                raise errors.AccessDenied(message=exc.message)

        return quota

    def get_admin_read_perm_quota(self, _id: str, user):
        """
        管理员查询有访问权限的的配额

        :param _id: 配额id
        :param user: 用户实例
        :return:
            UserQuota()

        :raises: QuotaError
        """
        quota = self.get_quota_by_id(_id)
        if not quota:
            raise errors.QuotaError.from_error(
                errors.NotFound(message='资源配额不存在'))

        if user.is_federal_admin():
            return quota

        if quota.service.user_has_perm(user):
            return quota

        raise errors.QuotaError.from_error(
            errors.AccessDenied(message=_('你无权限访问此配额'))
        )

    def delete_quota_soft(self, _id: str, user):
        """
        软删除用户的个人配额或vo组的配额

        :return:
            None                # success
            raise QuotaError    # failed

        :raises: QuotaError
        """
        quota = self.get_user_manage_perm_quota(_id=_id, user=user)
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
        return self.MODEL.objects.select_related('user', 'service').filter(user=user, deleted=False).all()

    def get_base_quota_queryset(self, user):
        """
        获取用户基本资源配额查询集

        :param user:用户对象
        :return: QuerySet()
        """
        return self.get_quota_queryset(user=user).filter(tag=self.MODEL.TAG_BASE).all()

    def get_quota_by_id(self, quota_id: str) -> UserQuota:
        """
        :param quota_id: 配额id
        :return:
            UserQuota() or None
        """
        return self.MODEL.objects.select_related('user', 'service', 'vo__owner').filter(id=quota_id).first()

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
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，指定的资源配额不存在'))

            if quota.classification == quota.Classification.PERSONAL:
                if quota.user_id != user.id:
                    raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))
            elif quota.classification == quota.Classification.VO:
                if quota.vo_id is None:
                    raise errors.NoSuchQuotaError(_('用户指定的vo资源配额没有vo关系'))
            else:
                raise errors.NoSuchQuotaError(_('用户指定的资源配额类型无法确认是个人还是vo配额'))

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
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，指定的资源配额不存在'))

            if quota.classification == quota.Classification.PERSONAL:
                if quota.user_id != user.id:
                    raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))
            elif quota.classification == quota.Classification.VO:
                if quota.vo_id is None:
                    raise errors.NoSuchQuotaError(_('用户指定的vo资源配额没有vo关系'))
            else:
                raise errors.NoSuchQuotaError(_('用户指定的资源配额类型无法确认是个人还是vo配额'))

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
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，指定的资源配额不存在'))

            if quota.classification == quota.Classification.PERSONAL:
                if quota.user_id != user.id:
                    raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))
            elif quota.classification == quota.Classification.VO:
                if quota.vo_id is None:
                    raise errors.NoSuchQuotaError(_('用户指定的vo资源配额没有vo关系'))
            else:
                raise errors.NoSuchQuotaError(_('用户指定的资源配额类型无法确认是个人还是vo配额'))

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
            quota = self.MODEL.objects.select_for_update().filter(id=quota_id).first()
            if not quota:
                raise errors.NoSuchQuotaError(_('参数无效，指定的资源配额不存在'))

            if quota.classification == quota.Classification.PERSONAL:
                if quota.user_id != user.id:
                    raise errors.NoSuchQuotaError(_('参数无效，用户没有指定的资源配额'))
            elif quota.classification == quota.Classification.VO:
                if quota.vo_id is None:
                    raise errors.NoSuchQuotaError(_('用户指定的vo资源配额没有vo关系'))
            else:
                raise errors.NoSuchQuotaError(_('用户指定的资源配额类型无法确认是个人还是vo配额'))

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

    def filter_user_quota_queryset(self, user, service=None, usable=None):
        """
        过滤用户个人的资源配额查询集

        :param user:
        :param service: 服务对象，暂时预留
        :param usable: 是否过滤可用的(未过有效期的)
        :return:
        """
        queryset = self.get_quota_queryset(user=user).filter(classification=self.MODEL.Classification.PERSONAL)
        if service:
            queryset = queryset.filter(service=service)

        if usable:
            now = timezone.now()
            queryset = queryset.filter(Q(expiration_time__isnull=True) | Q(expiration_time__gt=now))

        return queryset.order_by('id')

    def filter_vo_quota_queryset(self, vo, service=None, usable=None):
        """
        过滤vo组的资源配额查询集

        :param vo: vo组
        :param service: 服务对象，暂时预留
        :param usable: 是否过滤可用的(未过有效期的)
        :return:
        """
        queryset = self.MODEL.objects.select_related('user', 'service').filter(
            vo=vo, classification=ApplyQuota.Classification.VO, deleted=False)
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

    def update(self, service, vcpus: int = None, ram: int = None, disk_size: int = None,
               public_ip: int = None, private_ip: int = None, only_increase: bool = True):
        """
        更新资源总配额

        :param service: 接入服务实例
        :param vcpus: 虚拟cpu数
        :param ram: 内存，单位Mb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :param only_increase: True(只允许更新更大值，小于现有值抛出错误); False(更新任何大小的值)
        :return:
            self.MODEL()

        :raises: QuotaError, QuotaOnlyIncreaseError
        """
        with transaction.atomic():
            update_fields = []
            quota = self.MODEL.objects.select_for_update().filter(service=service).first()
            if not quota:
                quota = self._create_quota(service=service)
                if not quota:
                    raise errors.QuotaError(message=self._prefix_msg(_('创建资源配额失败')))

                quota = self.MODEL.objects.select_for_update().filter(service=service).first()

            if vcpus is not None:
                if only_increase and quota.vcpu_total > vcpus:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额vcpu只允许增加')))

                quota.vcpu_total = max(vcpus, 0)
                update_fields.append('vcpu_total')

            if ram is not None:
                if only_increase and quota.ram_total > ram:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额ram只允许增加')))

                quota.ram_total = max(ram, 0)
                update_fields.append('ram_total')

            if disk_size is not None:
                if only_increase and quota.disk_size_total > disk_size:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额disk只允许增加')))

                quota.disk_size_total = max(disk_size, 0)
                update_fields.append('disk_size_total')

            if public_ip is not None:
                if only_increase and quota.public_ip_total > public_ip:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额public ip只允许增加')))

                quota.public_ip_total = max(public_ip, 0)
                update_fields.append('public_ip_total')

            if private_ip is not None:
                if only_increase and quota.private_ip_total > private_ip:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额private ip只允许增加')))

                quota.private_ip_total = max(private_ip, 0)
                update_fields.append('private_ip_total')

            if update_fields:
                try:
                    quota.save(update_fields=update_fields)
                except Exception as e:
                    raise errors.QuotaError(message=self._prefix_msg(_('更新资源配额失败') + str(e)))

        return quota


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
    def get_service_by_id(_id):
        return ServiceConfig.objects.filter(id=_id).first()

    @staticmethod
    def filter_service(center_id: str, user=None):
        """
        :param center_id: 联邦成员机构id
        :param user: 用户对象，筛选用户有可用资源配额的服务
        """
        queryset = ServiceConfig.objects.select_related('data_center').filter(
            status=ServiceConfig.Status.ENABLE)

        if center_id:
            queryset = queryset.filter(data_center=center_id)

        if user:
            user_quotas = UserQuotaManager().filter_user_quota_queryset(user=user, usable=True)
            queryset = queryset.filter(id__in=Subquery(
                user_quotas.values_list('service_id', flat=True)))

        return queryset

    @staticmethod
    def filter_vo_service(center_id: str, vo):
        """
        :param center_id: 联邦成员机构id
        :param vo: vo组对象,筛选vo组有可用资源配额的服务
        """
        queryset = ServiceConfig.objects.select_related('data_center').filter(
            status=ServiceConfig.Status.ENABLE)

        if center_id:
            queryset = queryset.filter(data_center=center_id)

        user_quotas = UserQuotaManager().filter_vo_quota_queryset(vo=vo, usable=True)
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
    def get_service_id_map(use_cache=False, cache_seconds=60):
        """
        service id为key, service 实例为value的字典

        :param use_cache: True: 使用缓存方式；默认不使用，实时查询数据库
        :param cache_seconds: 缓存时间秒
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
                cache.set(caches_key, service_id_map, timeout=cache_seconds)

        return service_id_map


class OrganizationApplyManager:
    model = ApplyOrganization

    @staticmethod
    def get_apply_by_id(_id: str) -> ApplyOrganization:
        """
        :return:
            None                    # not exists
            ApplyOrganization()
        """
        return OrganizationApplyManager.model.objects.select_related(
            'user').filter(id=_id, deleted=False).first()

    def get_user_apply(self, _id: str, user) -> ApplyOrganization:
        """
        查询用户的申请

        :return:
            ApplyOrganization()

        :raises: Error
        """
        apply = self.get_apply_by_id(_id)
        if apply is None:
            raise errors.OrganizationApplyNotExists()

        if apply.user_id and apply.user_id == user.id:
            return apply

        raise errors.AccessDenied(message=_('无权限访问此申请'))

    @staticmethod
    def get_apply_queryset():
        return OrganizationApplyManager.model.objects.all()

    def get_not_delete_apply_queryset(self, user=None):
        filters = {
            'deleted': False
        }
        if user:
            filters['user'] = user

        qs = self.get_apply_queryset()
        return qs.filter(**filters)

    @staticmethod
    def filter_queryset(queryset, deleted: bool = None, status: list = None):
        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)

        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

    def filter_user_apply_queryset(self, user, deleted: bool = None, status: list = None):
        """
        过滤用户申请查询集

        :param user: 用户对象
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset().filter(user=user)
        return self.filter_queryset(queryset=queryset, deleted=deleted, status=status)

    def admin_filter_apply_queryset(self, deleted: bool = None, status: list = None):
        """
        管理员过滤申请查询集

        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset()
        return self.filter_queryset(queryset=queryset, deleted=deleted, status=status)

    def get_in_progress_apply_queryset(self, user=None):
        """
        处于申请中的申请查询集
        """
        qs = self.get_not_delete_apply_queryset(user=user)
        in_progress = [self.model.Status.WAIT, self.model.Status.PENDING]
        return qs.filter(status__in=in_progress)

    def get_in_progress_apply_count(self, user=None):
        """
        处于申请中的申请数量
        """
        qs = self.get_in_progress_apply_queryset(user=user)
        return qs.count()

    @staticmethod
    def create_apply(data: dict, user) -> ApplyOrganization:
        """
        创建一个机构申请

        :param data: dict, ApplyDataCenterSerializer.validated_data
        :param user:

        :raises: Error
        """
        apply = OrganizationApplyManager.model()
        apply.name = data.get('name')
        apply.name_en = data.get('name_en')
        apply.abbreviation = data.get('abbreviation')
        apply.independent_legal_person = data.get('independent_legal_person')
        apply.country = data.get('country')
        apply.city = data.get('city')
        apply.postal_code = data.get('postal_code')
        apply.address = data.get('address')
        apply.endpoint_vms = data.get('endpoint_vms')
        apply.endpoint_object = data.get('endpoint_object')
        apply.endpoint_compute = data.get('endpoint_compute')
        apply.endpoint_monitor = data.get('endpoint_monitor')
        apply.desc = data.get('desc')
        apply.logo_url = data.get('logo_url')
        apply.certification_url = data.get('certification_url')
        apply.user = user
        try:
            apply.save()
        except Exception as e:
            raise errors.Error.from_error(e)

        return apply

    def pending_apply(self, _id: str, user: UserProfile) -> ApplyOrganization:
        """
        挂起审批申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply is None:
            raise errors.OrganizationApplyNotExists()

        if apply.status == apply.Status.PENDING:
            return apply
        elif apply.status != apply.Status.WAIT:
            raise errors.ConflictError(message=_('只允许挂起处于“待审批”状态的资源配额申请'))

        apply.status = apply.Status.PENDING
        try:
            apply.save(update_fields=['status'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def cancel_apply(self, _id: str, user: UserProfile) -> ApplyOrganization:
        """
        取消申请

        :raises: Error
        """
        apply = self.get_user_apply(_id=_id, user=user)

        if apply.status == apply.Status.CANCEL:
            return apply
        elif apply.status != apply.Status.WAIT:
            raise errors.ConflictError(message=_('只允取消处于“待审批”状态的资源配额申请'))

        apply.status = apply.Status.CANCEL
        try:
            apply.save(update_fields=['status'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def delete_apply(self, _id: str, user: UserProfile) -> ApplyOrganization:
        """
        删除申请

        :raises: Error
        """
        apply = self.get_user_apply(_id=_id, user=user)
        if apply.status == apply.Status.PENDING:
            raise errors.ConflictError(message=_('不能删除审批中的申请'))
        if apply.deleted:
            return apply

        apply.deleted = True
        try:
            apply.save(update_fields=['deleted'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def reject_apply(self, _id: str, user: UserProfile) -> ApplyOrganization:
        """
        拒绝申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply is None:
            raise errors.OrganizationApplyNotExists()

        if apply.status == apply.Status.REJECT:
            return apply
        elif apply.status != apply.Status.PENDING:
            raise errors.ConflictError(message=_('只允拒绝处于“审批中”状态的资源配额申请'))

        apply.status = apply.Status.REJECT
        try:
            apply.save(update_fields=['status'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def pass_apply(self, _id: str, user: UserProfile) -> ApplyOrganization:
        """
        通过申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有访问权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply is None:
            raise errors.OrganizationApplyNotExists()

        if apply.is_pass():
            return apply
        elif apply.status != apply.Status.PENDING:
            raise errors.ConflictError(message=_('只允通过处于“审批中”状态的资源配额申请'))

        try:
            apply.do_pass_apply()
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply


class VmServiceApplyManager:
    model = ApplyVmService

    @staticmethod
    def get_apply_by_id(_id: str) -> ApplyVmService:
        """
        :return:
            None                    # not exists
            ApplyVmService()
        """
        return VmServiceApplyManager.model.objects.select_related(
            'user').filter(id=_id, deleted=False).first()

    def get_user_apply(self, _id: str, user) -> ApplyVmService:
        """
        查询用户的申请

        :return:
            ApplyVmService()

        :raises: Error
        """
        apply = self.get_apply_by_id(_id)
        if apply is None:
            raise errors.NotFound(message=_('申请不存在'))

        if apply.user_id and apply.user_id == user.id:
            return apply

        raise errors.AccessDenied(message=_('无权限访问此申请'))

    @staticmethod
    def get_apply_queryset():
        return VmServiceApplyManager.model.objects.all()

    @staticmethod
    def filter_queryset(queryset, deleted: bool = None, organization_id: str = None, status: list = None):
        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)

        if organization_id:
            queryset = queryset.filter(organization__id=organization_id)

        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

    def filter_user_apply_queryset(self, user, deleted: bool = None,
                                   organization_id: str = None, status: list = None):
        """
        过滤用户申请查询集

        :param user: 用户对象
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param organization_id: 机构id
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset().filter(user=user)
        return self.filter_queryset(queryset=queryset, deleted=deleted,
                                    organization_id=organization_id, status=status)

    def admin_filter_apply_queryset(self, deleted: bool = None,
                                    organization_id: str = None, status: list = None):
        """
        管理员过滤申请查询集

        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param organization_id: 机构id
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset()
        return self.filter_queryset(queryset=queryset, deleted=deleted,
                                    organization_id=organization_id, status=status)

    def get_not_delete_apply_queryset(self, user=None):
        filters = {
            'deleted': False
        }
        if user:
            filters['user'] = user

        qs = self.get_apply_queryset()
        return qs.filter(**filters)

    def get_in_progress_apply_queryset(self, user=None):
        """
        处于申请中的申请查询集
        """
        qs = self.get_not_delete_apply_queryset(user=user)
        in_progress = [self.model.Status.WAIT, self.model.Status.PENDING,
                       self.model.Status.FIRST_PASS, self.model.Status.TEST_PASS]
        return qs.filter(status__in=in_progress)

    def get_in_progress_apply_count(self, user=None):
        """
        处于申请中的申请数量
        """
        qs = self.get_in_progress_apply_queryset(user=user)
        return qs.count()

    @staticmethod
    def create_apply(data: dict, user) -> ApplyVmService:
        """
        创建一个服务接入申请

        :param data: dict, ApplyVmServiceSerializer.validated_data
        :param user:
        :return:
            ApplyVmService()

        :raises: Error
        """
        apply_service = VmServiceApplyManager.model()
        organization_id = data.get('organization_id')
        if not organization_id:
            raise errors.NoCenterBelongToError()

        center = DataCenter.objects.filter(id=organization_id).first()
        if center is None:
            raise errors.OrganizationNotExists()

        apply_service.organization_id = organization_id

        service_type = data.get('service_type')
        if service_type not in apply_service.ServiceType.values:
            raise errors.BadRequest(message='service_type值无效')

        apply_service.user = user
        apply_service.service_type = service_type
        apply_service.name = data.get('name')
        apply_service.name_en = data.get('name_en')
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
        apply_service.set_vpn_password(data.get('vpn_password', ''))
        apply_service.longitude = data.get('longitude', 0)
        apply_service.latitude = data.get('latitude', 0)
        apply_service.contact_person = data.get('contact_person', '')
        apply_service.contact_email = data.get('contact_email', '')
        apply_service.contact_telephone = data.get('contact_telephone', '')
        apply_service.contact_fixed_phone = data.get('contact_fixed_phone', '')
        apply_service.contact_address = data.get('contact_address', '')
        apply_service.logo_url = data.get('logo_url', '')

        try:
            apply_service.save()
        except Exception as e:
            raise errors.Error.from_error(e)

        return apply_service

    def cancel_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        取消申请

        :raises: Error
        """
        apply = self.get_user_apply(_id=_id, user=user)
        if apply.status == apply.Status.CANCEL:
            return apply

        if apply.status != apply.Status.WAIT:
            raise errors.ConflictError(message=_('不能取消待审批状态的申请'))

        apply.status = apply.Status.CANCEL
        try:
            apply.save(update_fields=['status'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def pending_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        挂起申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status == apply.Status.PENDING:
            return apply

        if apply.status != apply.Status.WAIT:
            raise errors.ConflictError(message=_('不能挂起处于待审批状态的申请'))

        apply.status = apply.Status.PENDING
        apply.approve_time = timezone.now()
        try:
            apply.save(update_fields=['status', 'approve_time'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def first_reject_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        初审拒绝申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status == apply.Status.FIRST_REJECT:
            return apply

        if apply.status != apply.Status.PENDING:
            raise errors.ConflictError(message=_('只能拒绝处于挂起状态的申请'))

        apply.status = apply.Status.FIRST_REJECT
        apply.approve_time = timezone.now()
        try:
            apply.save(update_fields=['status', 'approve_time'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def first_pass_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        初审通过申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status == apply.Status.FIRST_PASS:
            return apply

        if apply.status != apply.Status.PENDING:
            raise errors.ConflictError(message=_('只能审批通过处于挂起状态的申请'))

        apply.status = apply.Status.FIRST_PASS
        apply.approve_time = timezone.now()
        try:
            apply.save(update_fields=['status', 'approve_time'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def test_apply(self, _id: str, user: UserProfile) -> (ApplyVmService, str):
        """
        测试申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status not in [apply.Status.FIRST_PASS, apply.Status.TEST_PASS, apply.Status.TEST_FAILED]:
            raise errors.ConflictError(message=_('初审通过的申请才可以测试'))

        test_msg = ''
        test_result = apply.Status.TEST_PASS
        service = apply.convert_to_service()
        try:
            test_service_ok(service=service)
        except InvalidServiceError as exc:
            test_result = apply.Status.TEST_FAILED
            test_msg = str(exc)

        apply.status = test_result
        try:
            apply.save(update_fields=['status'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply, test_msg

    def reject_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        拒绝申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status == apply.Status.REJECT:
            return apply

        if apply.status == apply.Status.PASS:
            raise errors.ConflictError(message=_('不能再次审批已完成审批过程的申请'))

        if apply.status not in [apply.Status.FIRST_PASS, apply.Status.TEST_PASS, apply.Status.TEST_FAILED]:
            raise errors.ConflictError(message=_('只能审批通过初审的申请'))

        apply.status = apply.Status.REJECT
        apply.approve_time = timezone.now()
        try:
            apply.save(update_fields=['status', 'approve_time'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def pass_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        通过申请

        :raises: Error
        """
        if not user.is_federal_admin():
            raise errors.AccessDenied(message=_('你没有审批权限，需要联邦管理员权限'))

        apply = self.get_apply_by_id(_id=_id)
        if apply.status == apply.Status.PASS:
            return apply

        if apply.status == apply.Status.REJECT:
            raise errors.ConflictError(message=_('不能再次审批已完成审批过程的申请'))

        if apply.status not in [apply.Status.FIRST_PASS, apply.Status.TEST_PASS, apply.Status.TEST_FAILED]:
            raise errors.ConflictError(message=_('只能审批通过初审的申请'))

        try:
            apply.do_pass_apply()
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply

    def delete_apply(self, _id: str, user: UserProfile) -> ApplyVmService:
        """
        删除申请

        :raises: Error
        """
        apply = self.get_user_apply(_id=_id, user=user)
        if apply.status in [apply.Status.PENDING, apply.Status.FIRST_PASS, apply.Status.TEST_PASS]:
            raise errors.ConflictError(message=_('不能删除处于审批过程中的申请'))

        if apply.deleted:
            return apply

        apply.deleted = True
        try:
            apply.save(update_fields=['deleted'])
        except Exception as e:
            raise errors.APIException(message='更新数据库失败' + str(e))

        return apply


class ApplyQuotaManager:
    @staticmethod
    def get_apply(pk):
        """
        :raises: Error
        """
        apply = ApplyQuota.objects.select_related('service', 'vo__owner').filter(id=pk, deleted=False).first()
        if not apply:
            raise errors.NotFound(message=_('资源配额申请不存在'))

        return apply

    def get_user_or_vo_apply(self, pk, user):
        """
        查询用户自己的申请, 或vo组申请（用户需是vo组管理员）
        :raises: Error
        """
        apply = self.get_apply(pk)
        if apply.classification == apply.Classification.PERSONAL:
            if not apply.user_id or apply.user_id != user.id:
                raise errors.AccessDenied(message=_('你没有权限操作此配额申请'))
        elif apply.classification == apply.Classification.VO:
            if apply.vo is None:
                raise errors.ConflictError(message=_('vo组配额申请，vo组信息丢失，无法判断你是否有权限访问'))

            try:
                VoManager.check_manager_perm(vo=apply.vo, user=user)
            except errors.Error as exc:
                raise errors.AccessDenied(message=_('vo组配额申请,') + exc.message)

        return apply

    def get_has_manage_perm_apply(self, pk, user):
        """
        查询用户有权限审批的申请
        :raises: Error
        """
        apply = self.get_apply(pk)
        if not apply.service.user_has_perm(user):
            raise errors.AccessDenied(message=_('没有审批操作资源配额申请的权限'))

        return apply

    @staticmethod
    def get_apply_queryset():
        return ApplyQuota.objects.all()

    def get_no_deleted_apply_queryset(self):
        queryset = self.get_apply_queryset()
        return queryset.filter(deleted=False)

    def get_admin_apply_queryset(self, user, service_id=None):
        """
        查询用户可管理审批的申请查询集
        """
        services = user.service_set.all()
        queryset = self.get_apply_queryset()
        return queryset.filter(
            service__in=Subquery(services.values_list('id', flat=True))
            ).all()

    @staticmethod
    def filter_queryset(queryset, service_id: str = None, deleted: bool = None,
                        status: list = None):
        if service_id:
            queryset = queryset.filter(service_id=service_id)

        if deleted is not None:
            queryset = queryset.filter(deleted=deleted)

        if status:
            queryset = queryset.filter(status__in=status)

        return queryset

    def filter_user_apply_queryset(self, user, service_id: str = None, deleted: bool = None,
                                   status: list = None):
        """
        过滤用户个人的申请查询集

        :param user: 用户对象
        :param service_id: 服务id
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset().select_related('service', 'user').filter(
            user=user, classification=ApplyQuota.Classification.PERSONAL)
        return self.filter_queryset(queryset=queryset, service_id=service_id,
                                    deleted=deleted, status=status)

    def admin_filter_apply_queryset(self, user=None, service_id: str = None, deleted: bool = None,
                                    status: list = None):
        """
        管理员过滤申请查询集

        :param user: 管理用户对象,筛选用户用权限管理的申请记录，默认None不筛选
        :param service_id: 服务id
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        if user:
            queryset = self.get_admin_apply_queryset(user)
        else:
            queryset = self.get_apply_queryset()

        return self.filter_queryset(queryset=queryset, service_id=service_id,
                                    deleted=deleted, status=status)

    def filter_vo_apply_queryset(self, vo, service_id: str = None, deleted: bool = None,
                                 status: list = None):
        """
        过滤vo组的申请查询集

        :param vo: vo组对象
        :param service_id: 服务id
        :param deleted: 删除状态筛选，默认不筛选，True(已删除申请记录)，False(未删除申请记录)
        :param status: 过滤指定状态的申请记录
        """
        queryset = self.get_apply_queryset().filter(
            vo=vo, classification=ApplyQuota.Classification.VO)
        return self.filter_queryset(queryset=queryset, service_id=service_id,
                                    deleted=deleted, status=status)

