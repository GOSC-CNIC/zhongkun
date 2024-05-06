from decimal import Decimal

from django.utils.translation import gettext_lazy, gettext as _
from django.utils import timezone
from django.db import transaction
from django.db.models import Subquery, Q

from django.core.cache import cache

from core import errors
from core import request as core_request
from apps.vo.managers import VoManager
from apps.app_wallet.managers import PaymentManager
from utils.model import PayType, OwnerType
from apps.storage.serializers import BucketSerializer
from apps.storage.models import Bucket
from apps.servers.disk_serializers import DiskSerializer
from apps.servers.serializers import ServerSerializer
from apps.servers.models import (
    Server, ServerArchive, Flavor, Disk, ResourceActionLog, ServiceConfig, ServicePrivateQuota, ServiceShareQuota
)
from .server_instance import ServerInstance


class ServiceManager:
    @staticmethod
    def get_service_by_id(_id):
        return ServiceConfig.objects.filter(id=_id).first()

    @staticmethod
    def get_service(service_id):
        """
        :raises: Error
        """
        service = ServiceConfig.objects.select_related(
            'org_data_center', 'org_data_center__organization').filter(id=service_id).first()
        if not service:
            raise errors.ServiceNotExist(_('资源提供者服务不存在'))

        if service.status != ServiceConfig.Status.ENABLE.value:
            raise errors.ServiceStopped(_('资源提供者服务停止服务'))

        return service

    def get_server_service(self, _id):
        """
        :raises: Error
        """
        return self.get_service(_id)

    @staticmethod
    def filter_service(org_id: str, center_id: str, status: str):
        """
        :param org_id: 机构id
        :param center_id: 机构数据中心
        :param status: 服务单元服务状态
        """
        queryset = ServiceConfig.objects.select_related('org_data_center', 'org_data_center__organization').all()

        if status:
            queryset = queryset.filter(status=status)

        if center_id:
            queryset = queryset.filter(org_data_center_id=center_id)

        if org_id:
            queryset = queryset.filter(org_data_center__organization_id=org_id)

        return queryset.order_by('-add_time')

    @staticmethod
    def _get_perm_service_qs(user_id: str):
        return ServiceConfig.objects.select_related(
            'org_data_center', 'org_data_center__organization'
        ).filter(
            Q(users__id=user_id) | Q(org_data_center__users__id=user_id)
        ).distinct()

    @staticmethod
    def get_has_perm_service(user):
        """
        用户有权限管理的服务
        """
        qs = ServiceManager._get_perm_service_qs(user_id=user.id)
        return qs.filter(status=ServiceConfig.Status.ENABLE).order_by('-add_time')

    @staticmethod
    def get_all_has_perm_service(user):
        """
        用户有权限管理的所有服务
        """
        return ServiceManager._get_perm_service_qs(user_id=user.id)

    @staticmethod
    def get_has_perm_service_ids(user_id: str):
        return ServiceConfig.objects.filter(
            Q(users__id=user_id) | Q(org_data_center__users__id=user_id)
        ).distinct().values_list('id', flat=True)

    @staticmethod
    def get_service_if_admin(user, service_id: str):
        """
        用户是指定云主机服务的管理员

        :return:
            ServiceConfig()     # 是
            None                # 不是
        """
        qs = ServiceManager._get_perm_service_qs(user_id=user.id)
        return qs.filter(id=service_id).first()

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
            services = ServiceConfig.objects.select_related('org_data_center').all()
            service_id_map = {}
            for s in services:
                service_id_map[s.id] = s

            if use_cache:
                cache.set(caches_key, service_id_map, timeout=cache_seconds)

        return service_id_map

    @staticmethod
    def has_perm(user_id, service_id):
        qs = ServiceManager._get_perm_service_qs(user_id=user_id)
        return qs.filter(id=service_id).exists()

    @staticmethod
    def update_service_version(service: ServiceConfig):
        try:
            r = core_request.request_service(service=service, method='get_version')
            if r.version:
                service.version = r.version
                service.save(update_fields=['version'])
        except Exception as exc:
            return exc

        return True


class ServerManager:
    @staticmethod
    def get_server_queryset():
        return Server.objects.all()

    def get_user_servers_queryset(
            self, user, service_id: str = None, ipv4_contains: str = None, expired: bool = None,
            public: bool = None, remark: str = None, pay_type: str = None
    ):
        """
        查询用户个人server

        :param user: 用户过滤
        :param service_id: 服务单元id过滤
        :param ipv4_contains: ip包含过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :param public: True(公网ip), False(私网ip)
        :param remark: 备注模糊查询
        :param pay_type: 付费模式
        :return: QuerySet()
        """
        lookups = {}
        if public is not None:
            lookups['public_ip'] = public

        if ipv4_contains:
            lookups['ipv4__contains'] = ipv4_contains

        if service_id:
            lookups['service_id'] = service_id

        if pay_type is not None:
            lookups['pay_type'] = pay_type

        if remark:
            lookups['remarks__icontains'] = remark

        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user', 'vo').filter(
            user=user, classification=Server.Classification.PERSONAL, **lookups)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))     # 取反的方式，存在expiration_time == None

        return qs

    def get_admin_servers_queryset(
            self, user, service_id: str = None, ipv4_contains: str = None, expired: bool = None,
            vo_id: str = None, vo_name: str = None, user_id: str = None, username: str = None,
            exclude_vo: bool = None, public: bool = None, remark: str = None, pay_type: str = None
    ):
        """
        管理员查询server

        :param user: 管理员用户
        :param service_id: 服务单元id过滤
        :param user_id: 过滤用户, 包括vo内的用户创建的
        :param username: 过滤用户名,模糊查询, 包括vo内的用户创建的
        :param vo_id: 过滤vo
        :param ipv4_contains: ip包含过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :param vo_name: 过滤vo组名,模糊查询
        :param exclude_vo: True(排除vo组的server)，其他忽略
        :param public: True(公网ip), False(私网ip)
        :param remark: 备注模糊查询
        :param pay_type: 付费模式
        :return: QuerySet()
        :raises: Error
        """
        admin_user = user
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user', 'vo')

        if user_id:
            qs = qs.filter(user_id=user_id)

        if username:
            qs = qs.filter(user__username__icontains=username)

        if exclude_vo:
            qs = qs.filter(classification=Server.Classification.PERSONAL.value)

        if public is True:
            qs = qs.filter(public_ip=True)
        elif public is False:
            qs = qs.filter(public_ip=False)

        if pay_type is not None:
            qs = qs.filter(pay_type=pay_type)

        if vo_id or vo_name:
            lookups = {'classification': Server.Classification.VO.value}
            if vo_id:
                lookups['vo_id'] = vo_id
            if vo_name:
                lookups['vo__name__icontains'] = vo_name
            qs = qs.filter(**lookups)

        if user.is_federal_admin():
            if service_id:
                qs = qs.filter(service_id=service_id)
        else:
            if service_id:
                service = ServiceManager.get_service_if_admin(user=admin_user, service_id=service_id)
                if service is None:
                    raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

                qs = qs.filter(service_id=service_id)
            else:
                subq = Subquery(ServiceManager.get_has_perm_service_ids(user_id=admin_user.id))
                qs = qs.filter(service_id__in=subq)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now(), pay_type=PayType.PREPAID.value)
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))

        if ipv4_contains:
            qs = qs.filter(ipv4__contains=ipv4_contains)

        if remark:
            qs = qs.filter(remarks__icontains=remark)

        return qs

    def get_vo_servers_queryset(self, vo_id: str, service_id: str = None, expired: bool = None, pay_type: str = None):
        """
        查询vo组的server
        """
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user', 'vo').filter(
            vo_id=vo_id, classification=Server.Classification.VO)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))

        if pay_type:
            qs = qs.filter(pay_type=pay_type)

        return qs

    @staticmethod
    def get_server(server_id: str, related_fields: list = None, select_for_update: bool = False) -> Server:
        fields = ['service', 'user']
        if related_fields:
            for f in related_fields:
                if f not in fields:
                    fields.append(f)
        qs = Server.objects.filter(id=server_id).select_related(*fields)
        if select_for_update:
            qs = qs.select_for_update()

        server = qs.first()
        if not server:
            raise errors.NotFound(_('服务器实例不存在'))

        return server

    def get_permission_server(self, server_id: str, user, related_fields: list = None,
                              read_only: bool = True) -> Server:
        """
        查询用户指定权限的虚拟服务器实例

        :raises: Error
        """
        if related_fields and 'vo' not in related_fields:
            related_fields.append('vo')

        server = self.get_server(server_id=server_id, related_fields=related_fields)
        if server.classification == server.Classification.PERSONAL:
            if not server.user_has_perms(user):
                raise errors.AccessDenied(_('无权限访问此服务器实例'))
        elif server.classification == server.Classification.VO:
            if server.vo is None:
                raise errors.ConflictError(message=_('vo组信息丢失，无法判断你是否有权限访问'))

            try:
                if read_only:
                    VoManager.check_read_perm(vo=server.vo, user=user)
                else:
                    VoManager.check_manager_perm(vo=server.vo, user=user)
            except errors.Error as exc:
                raise errors.AccessDenied(message=exc.message)

        return server

    def get_permission_server_as_admin(self, server_id: str, user, related_fields: list = None,
                                       read_only: bool = True) -> Server:
        """
        查询作为管理员用户指定权限的虚拟服务器实例

        :raises: Error
        """
        server = self.get_server(server_id=server_id, related_fields=related_fields)
        if user.is_federal_admin():
            return server
        else:
            service = ServiceManager.get_service_if_admin(user=user, service_id=server.service.id)
            if service is not None:
                return server

        raise errors.AccessDenied(_('您没有管理权限，无权限访问此服务器实例'))

    def get_manage_perm_server(self, server_id: str, user, related_fields: list = None,
                               as_admin: bool = False) -> Server:
        """
        查询用户有管理权限的虚拟服务器实例
        :raises: Error
        """
        if as_admin:
            return self.get_permission_server_as_admin(
                server_id=server_id, user=user, related_fields=related_fields, read_only=False)

        return self.get_permission_server(server_id=server_id, user=user, related_fields=related_fields,
                                          read_only=False)

    def get_read_perm_server(self, server_id: str, user, related_fields: list = None, as_admin: bool = False) -> Server:
        """
        查询用户有访问权限的虚拟服务器实例
        :raises: Error
        """
        if as_admin:
            return self.get_permission_server_as_admin(server_id=server_id, user=user, related_fields=related_fields)

        return self.get_permission_server(server_id=server_id, user=user, related_fields=related_fields,
                                          read_only=True)

    @staticmethod
    def get_server_or_archive(server_id: str):
        """
        查询一个云主机或者已删除归档的云主机
        :return:
            Server() or ServerArchive()
            None
        """
        server = Server.objects.filter(id=server_id).first()
        if server is not None:
            return server

        archieve = ServerArchive.objects.filter(
            server_id=server_id, archive_type=ServerArchive.ArchiveType.ARCHIVE.value).first()
        return archieve

    @staticmethod
    def check_situation_suspend(server: Server):
        """
        检测云主机是否过期，欠费被停服挂起
        * 如果云主机处于欠费挂起状态，查询用户是否补交欠款，不再欠费，不再欠费的话就停止云主机“停服挂起“状态恢复正常；
        * 如果云主机处于过期挂起状态，查询云主机是否续费，不再过期的话就停止云主机“停服挂起“状态恢复正常；

        :raises: Error
        """
        if server.situation == Server.Situation.NORMAL.value:
            return
        elif server.situation == Server.Situation.EXPIRED.value:
            if server.expiration_time and server.expiration_time <= timezone.now():
                raise errors.ExpiredSuspending(message=_('云主机过期停机停服挂起中'))
            server.set_situation_normal()
        elif server.situation == Server.Situation.ARREARAGE.value:
            if server.pay_type == PayType.PREPAID.value:    # 包年包月预付费不应该欠费挂起
                server.set_situation_normal()
                return

            if server.service is None:
                raise errors.ArrearageSuspending(
                    message=_('云主机欠费停机停服挂起中，云主机所属服务未知，无法查询用户或vo组是否还欠费'))

            if not server.service.pay_app_service_id:
                raise errors.ArrearageSuspending(
                    message=_('云主机所属服务单元没有配置余额结算系统app服务id，无法查询用户或vo组是否还欠费'))

            if not ServerManager.is_server_arrearage(server=server):
                server.set_situation_normal()
            else:
                raise errors.ArrearageSuspending(message=_('云主机欠费停机停服挂起中'))
        else:
            raise errors.ConflictError(message=_('云主机管控状态未知'))

    @staticmethod
    def is_server_arrearage(server: Server):
        """
        按量付费云主机是否欠费
        :return:
            True    # 欠费
            False   # 不欠费
        :raises: Error
        """
        if server.pay_type != PayType.POSTPAID.value:
            return False

        if server.belong_to_vo():
            ok = PaymentManager().has_enough_balance_vo(
                vo_id=server.vo_id, money_amount=Decimal('0'), with_coupons=True,
                app_service_id=server.service.pay_app_service_id
            )
        else:
            ok = PaymentManager().has_enough_balance_user(
                user_id=server.user_id, money_amount=Decimal('0'), with_coupons=True,
                app_service_id=server.service.pay_app_service_id
            )

        return not ok

    @staticmethod
    def not_allow_start_server_check(server: Server):
        """
        云主机过期，或者按量模式欠费不允许开机

        :raises: Error
        """
        # 预付费云主机，过期不允许开机；
        if server.pay_type == PayType.PREPAID.value:
            if server.expiration_time and server.expiration_time <= timezone.now():
                raise errors.ExpiredSuspending(message=_('云主机已过期，不允许开机，请完成续费后重试。'))
        # 按量计费云主机，欠费不允许开机；
        else:
            if ServerManager.is_server_arrearage(server):
                raise errors.ArrearageSuspending(
                    message=_('云主机已欠费，不允许开机，请充值后或者获得云主机所属服务单元的资源券后重试。'))

    def do_arrearage_suspend_server(self, server: Server):
        """
        云服务器欠费，关机挂起

        :raises: Error
        """
        self.do_suspend_server(server=server,situation=Server.Situation.ARREARAGE.value)

    def do_expired_suspend_server(self, server: Server):
        """
        云服务器过期，关机挂起

        :raises: Error
        """
        self.do_suspend_server(server=server,situation=Server.Situation.EXPIRED.value)

    def do_suspend_server_normal(self, server: Server):
        """
        取消云服务器过期，关机挂起状态

        :raises: Error
        """
        self.do_suspend_server(server=server, situation=Server.Situation.NORMAL.value)

    @staticmethod
    def do_suspend_server(server: Server, situation: str):
        """
        云服务器欠费或过期，关机挂起

        :raises: Error
        """
        if situation not in Server.Situation.values:
            raise errors.Error(message=_('设置过期欠费管控状态值无效'))

        if situation in [Server.Situation.EXPIRED.value, Server.Situation.ARREARAGE.value]:
            si = ServerInstance(server)
            si.action(act=si.ServerAction.POWER_OFF)
            status_code, status_text = si.status()
            if status_code not in [si.ServerStatus.SHUTOFF, si.ServerStatus.SHUTDOWN]:
                si.action(act=si.ServerAction.POWER_OFF)

        server.situation = situation
        server.situation_time = timezone.now()
        try:
            server.save(update_fields=['situation', 'situation_time'])
        except Exception as exc:
            raise errors.Error.from_error(exc)

    @staticmethod
    def has_server_in_service(service_id: str, user_id: str) -> bool:
        """
        用户在指定服务中是否拥有云主机资源
        """
        return Server.objects.filter(
            service_id=service_id, user_id=user_id, classification=Server.Classification.PERSONAL.value
        ).exists()

    @staticmethod
    def has_vo_server_in_service(service_id: str, user) -> bool:
        """
        用户所在的vo组在指定服务中是否拥有云主机资源
        """
        queryset = VoManager().get_user_vo_queryset(user=user, owner=True, member=True)
        vo_ids = queryset.values_list('id', flat=True)
        return Server.objects.filter(
            service_id=service_id, vo_id__in=vo_ids, classification=Server.Classification.VO.value
        ).exists()


class ServerArchiveManager:
    @staticmethod
    def get_archives_queryset():
        return ServerArchive.objects.all()

    def get_user_archives_queryset(self, user, service_id: str = None):
        """
        查询用户个人server归档记录
        """
        qs = self.get_archives_queryset()
        qs = qs.select_related('service').filter(
            user=user, classification=ServerArchive.Classification.PERSONAL,
            archive_type=ServerArchive.ArchiveType.ARCHIVE)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def get_vo_archives_queryset(self, vo_id: str, service_id: str = None):
        """
        查询vo组的server归档记录
        """
        qs = self.get_archives_queryset()
        qs = qs.select_related('service').filter(
            vo_id=vo_id, classification=ServerArchive.Classification.VO,
            archive_type=ServerArchive.ArchiveType.ARCHIVE)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs


class FlavorManager:
    @staticmethod
    def get_enable_flavor(_id):
        return Flavor.objects.filter(id=_id, enable=True).first()

    @staticmethod
    def get_flavor_queryset():
        return Flavor.objects.all()

    @staticmethod
    def filter_queryset(queryset, service_ids: list, enable: bool = None):
        if service_ids:
            if len(service_ids) == 1:
                queryset = queryset.filter(service_id=service_ids[0])
            else:
                queryset = queryset.filter(service_id__in=service_ids)

        if enable is not None:
            queryset = queryset.filter(enable=enable)

        return queryset

    def get_admin_flavor_queryset(self, user, service_id: str, enable: bool = None):
        queryset = self.get_flavor_queryset()
        queryset = queryset.order_by('vcpus', 'ram')
        if user.is_federal_admin():
            service_ids = [service_id] if service_id else []
            return self.filter_queryset(queryset=queryset, service_ids=service_ids, enable=enable)

        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有服务单元的访问权限'))

            service_ids = [service_id]
        else:
            service_ids = list(user.service_set.all().values_list('id', flat=True))
            if not service_ids:
                return queryset.none()

        return self.filter_queryset(queryset=queryset, service_ids=service_ids, enable=enable)


class DiskManager:
    @staticmethod
    def get_disk_queryset():
        return Disk.objects.filter(deleted=False)

    @staticmethod
    def get_disk(disk_id: str, related_fields: list = None, select_for_update: bool = False) -> Disk:
        """
        :raise: DiskNotExist
        """
        disk = DiskManager.get_disk_include_deleted(
            disk_id=disk_id, related_fields=related_fields, select_for_update=select_for_update)

        if disk.deleted:
            raise errors.DiskNotExist(message=_('云硬盘不存在'))

        return disk

    @staticmethod
    def get_disk_include_deleted(disk_id: str, related_fields: list = None, select_for_update: bool = False) -> Disk:
        """
        :raise: DiskNotExist
        """
        fields = ['service', 'user']
        if related_fields:
            for f in related_fields:
                if f not in fields:
                    fields.append(f)

        qs = Disk.objects.filter(id=disk_id).select_related(*fields)
        if select_for_update:
            qs = qs.select_for_update()

        disk = qs.first()
        if disk is None:
            raise errors.DiskNotExist(message=_('云硬盘不存在'))

        return disk

    def get_read_perm_disk(self, disk_id: str, user) -> Disk:
        """
        查询用户有读权限的云硬盘

        :raise: DiskNotExist, AccessDenied
        """
        disk = self.get_disk(disk_id=disk_id)
        if disk.classification == Disk.Classification.PERSONAL.value and disk.user_id == user.id:
            return disk
        elif disk.classification == Disk.Classification.VO.value:
            try:
                VoManager().get_has_read_perm_vo(vo_id=disk.vo_id, user=user)
                return disk
            except errors.Error as exc:
                raise errors.AccessDenied(message=_('你没有硬盘所属项目组的访问权限'))
        else:
            raise errors.AccessDenied(message=_('你没有硬盘的访问权限'))

    def get_manage_perm_disk(self, disk_id: str, user) -> Disk:
        """
        查询用户有管理权限的云硬盘

        :raise: DiskNotExist, AccessDenied
        """
        disk = self.get_disk(disk_id=disk_id)
        if disk.classification == Disk.Classification.PERSONAL.value and disk.user_id == user.id:
            return disk
        elif disk.classification == Disk.Classification.VO.value:
            try:
                VoManager().get_has_manager_perm_vo(vo_id=disk.vo_id, user=user)
                return disk
            except errors.Error as exc:
                raise errors.AccessDenied(message=_('你没有硬盘所属项目组的管理权限'))
        else:
            raise errors.AccessDenied(message=_('你没有硬盘的管理权限'))

    def admin_get_disk(self, disk_id: str, user) -> Disk:
        """
        查询有管理员权限的云硬盘

        :raise: DiskNotExist, AccessDenied
        """
        disk: Disk = self.get_disk(disk_id=disk_id)
        if user.is_federal_admin():
            return disk

        service_id = disk.service_id
        if service_id and isinstance(service_id, str):
            if ServiceManager.get_service_if_admin(service_id=service_id, user=user):
                return disk

        raise errors.AccessDenied(message=_('你没有硬盘的管理权限。'))

    @staticmethod
    def filter_disk_queryset(
            queryset, service_ids: list, volume_min: int, volume_max: int,
            remark: str, pay_type, expired: bool = None, ipv4_contains: str = None,
    ):
        if volume_min and volume_max and volume_min > volume_max:
            return queryset.none()

        lookups = {}
        if service_ids:
            if len(service_ids) == 1:
                lookups['service_id'] = service_ids[0]
            else:
                lookups['service_id__in'] = service_ids

        if volume_min and volume_min > 0:
            lookups['size__gte'] = volume_min

        if volume_max:
            if volume_max > 0:
                lookups['size__lte'] = volume_max
            else:
                return queryset.none()

        if pay_type is not None:
            lookups['pay_type'] = pay_type

        if remark:
            lookups['remarks__icontains'] = remark

        if ipv4_contains:
            lookups['server__ipv4__contains'] = ipv4_contains

        if expired is True:
            queryset = queryset.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            queryset = queryset.filter(~Q(expiration_time__lte=timezone.now()))

        queryset = queryset.filter(**lookups)
        return queryset

    def get_user_disks_queryset(
            self, user, volume_min: int = None, volume_max: int = None, service_id: str = None,
            expired: bool = None, remark: str = None, pay_type: str = None, ipv4_contains: str = None
    ):
        """
        查询用户个人云硬盘

        :param user: 用户过滤
        :param volume_min: 最小容量
        :param volume_max: 最大容量
        :param service_id: 服务单元id过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :param remark: 备注模糊查询
        :param pay_type: 付费模式
        :param ipv4_contains:
        :return: QuerySet()
        """
        qs = self.get_disk_queryset()
        qs = qs.select_related('service', 'user', 'server').filter(
            user=user, classification=Disk.Classification.PERSONAL.value)

        service_ids = [service_id] if service_id else None
        qs = self.filter_disk_queryset(
            queryset=qs, service_ids=service_ids, volume_min=volume_min, volume_max=volume_max,
            pay_type=pay_type, remark=remark, expired=expired, ipv4_contains=ipv4_contains
        )

        return qs

    def get_vo_disks_queryset(
            self, vo_id: str, volume_min: int = None, volume_max: int = None,
            service_id: str = None, expired: bool = None, pay_type: str = None,
            remark: str = None, ipv4_contains: str = None
    ):
        """
        查询vo组的disk
        """
        qs = self.get_disk_queryset()
        qs = qs.select_related('service', 'user', 'vo', 'server').filter(
            vo_id=vo_id, classification=Disk.Classification.VO.value)

        service_ids = [service_id] if service_id else None
        qs = self.filter_disk_queryset(
            queryset=qs, service_ids=service_ids, volume_min=volume_min, volume_max=volume_max,
            pay_type=pay_type, remark=remark, expired=expired, ipv4_contains=ipv4_contains
        )

        return qs

    def get_admin_disk_queryset(
            self, user, volume_min: int, volume_max: int, service_id: str = None, expired: bool = None,
            remark: str = None, pay_type: str = None, ipv4_contains: str = None,
            vo_id: str = None, vo_name: str = None, user_id: str = None, username: str = None,
            exclude_vo: bool = None
    ):
        """
        管理员查询disk

        :param user: 管理员用户
        :param volume_min: 最小容量
        :param volume_max: 最大容量
        :param service_id: 服务单元id过滤
        :param user_id: 过滤用户, 包括vo内的用户创建的
        :param username: 过滤用户名,模糊查询, 包括vo内的用户创建的
        :param vo_id: 过滤vo
        :param ipv4_contains: ip包含过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :param vo_name: 过滤vo组名,模糊查询
        :param exclude_vo: True(排除vo组的server)，其他忽略
        :param remark: 备注模糊查询
        :param pay_type: 付费模式
        :return: QuerySet()
        :raises: Error
        """
        qs = self.get_disk_queryset()
        qs = qs.select_related('service', 'user', 'vo', 'server')

        if user_id:
            qs = qs.filter(user_id=user_id)

        if username:
            qs = qs.filter(user__username__icontains=username)

        if exclude_vo:
            qs = qs.filter(classification=Server.Classification.PERSONAL.value)

        if vo_id or vo_name:
            lookups = {'classification': Server.Classification.VO.value}
            if vo_id:
                lookups['vo_id'] = vo_id
            if vo_name:
                lookups['vo__name__icontains'] = vo_name
            qs = qs.filter(**lookups)

        if user.is_federal_admin():
            if service_id:
                service_ids = [service_id]
            else:
                service_ids = None
        elif service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

            service_ids = [service_id]
        else:
            service_ids = ServiceManager.get_has_perm_service_ids(user_id=user.id)
            if not service_ids:
                return qs.none()

        qs = self.filter_disk_queryset(
            queryset=qs, service_ids=service_ids, volume_min=volume_min, volume_max=volume_max,
            pay_type=pay_type, remark=remark, expired=expired, ipv4_contains=ipv4_contains
        )

        return qs

    @staticmethod
    def get_server_disks_qs(server_id: str):
        return Disk.objects.select_related('server').filter(server_id=server_id, deleted=False)


class ResourceActionLogManager:
    @staticmethod
    def add_delete_log_for_resource(res, user, raise_error: bool = True):
        try:
            return ResourceActionLogManager.add_log_for_resource(
                res=res, user=user, action_flag=ResourceActionLog.ActionFlag.DELETION.value
            )
        except Exception as exc:
            if raise_error:
                raise exc

    @staticmethod
    def add_log_for_resource(res, user, action_flag: str):
        resource_id = res.id
        resource_repr = str(res)
        if isinstance(res, Server):
            resource_type = ResourceActionLog.ResourceType.SERVER.value
            resource_message = ServerSerializer(instance=res).data
            if res.classification == Server.Classification.PERSONAL.value:
                owner_id = res.user_id
                owner_name = res.user.username
                owner_type = OwnerType.USER.value
            else:
                owner_id = res.vo_id
                owner_name = res.vo.name
                owner_type = OwnerType.VO.value
        elif isinstance(res, Disk):
            resource_type = ResourceActionLog.ResourceType.DISK.value
            resource_message = DiskSerializer(instance=res).data
            if res.classification == Server.Classification.PERSONAL.value:
                owner_id = res.user_id
                owner_name = res.user.username
                owner_type = OwnerType.USER.value
            else:
                owner_id = res.vo_id
                owner_name = res.vo.name
                owner_type = OwnerType.VO.value
        elif isinstance(res, Bucket):
            resource_type = ResourceActionLog.ResourceType.BUCHET.value
            resource_message = BucketSerializer(instance=res).data
            owner_id = res.user_id
            owner_name = res.user.username
            owner_type = OwnerType.USER.value
        else:
            return None

        return ResourceActionLogManager.add_log(
            user_id=user.id, username=user.username, action_flag=action_flag,
            resource_type=resource_type, resource_id=resource_id, resource_repr=resource_repr,
            resource_message=resource_message,
            owner_id=owner_id, owner_name=owner_name, owner_type=owner_type
        )

    @staticmethod
    def add_log(
            user_id, username: str, action_flag: str, resource_type: str,
            resource_id, resource_repr, resource_message: dict,
            owner_id, owner_name, owner_type
    ):
        log = ResourceActionLog(
            action_time=timezone.now(),
            user_id=user_id, username=username, action_flag=action_flag, resource_type=resource_type,
            resource_id=resource_id, resource_repr=resource_repr, resource_message=resource_message,
            owner_id=owner_id, owner_name=owner_name, owner_type=owner_type
        )
        log.save(force_insert=True)
        return log


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

    def deduct(self, service, vcpus: int = 0, ram_gib: int = 0, disk_size: int = 0,
               public_ip: int = 0, private_ip: int = 0):
        """
        扣除资源

        :param service: 接入服务
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram_gib < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
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
                # 默认<=0，不限制资源
                if quota.vcpu_total <= 0 or (quota.vcpu_total - quota.vcpu_used) >= vcpus:
                    quota.vcpu_used = quota.vcpu_used + vcpus
                    update_fields.append('vcpu_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('vCPU资源配额不足')))

            if ram_gib > 0:
                if quota.ram_total <= 0 or (quota.ram_total - quota.ram_used) >= ram_gib:
                    quota.ram_used = quota.ram_used + ram_gib
                    update_fields.append('ram_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('Ram资源配额不足')))

            if disk_size > 0:
                if quota.disk_size_total <= 0 or (quota.disk_size_total - quota.disk_size_used) >= disk_size:
                    quota.disk_size_used = quota.disk_size_used + disk_size
                    update_fields.append('disk_size_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('硬盘资源配额不足')))

            if public_ip > 0:
                if quota.public_ip_total <= 0 or (quota.public_ip_total - quota.public_ip_used) >= public_ip:
                    quota.public_ip_used = quota.public_ip_used + public_ip
                    update_fields.append('public_ip_used')
                else:
                    raise errors.QuotaShortageError(message=self._prefix_msg(_('公网IP资源配额不足')))

            if private_ip > 0:
                if quota.private_ip_total <= 0 or (quota.private_ip_total - quota.private_ip_used) >= private_ip:
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

    def release(self, service, vcpus: int = 0, ram_gib: int = 0, disk_size: int = 0,
                public_ip: int = 0, private_ip: int = 0):
        """
        释放已用的资源

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram_gib < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
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

            if ram_gib > 0:
                quota.ram_used = max(quota.ram_used - ram_gib, 0)
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

    def increase(self, service, vcpus: int = 0, ram_gib: int = 0, disk_size: int = 0,
                 public_ip: int = 0, private_ip: int = 0):
        """
        增加总资源配额

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram_gib < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
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

            if ram_gib > 0:
                quota.ram_total = quota.ram_total + ram_gib
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

    def decrease(self, service, vcpus: int = 0, ram_gib: int = 0, disk_size: int = 0,
                 public_ip: int = 0, private_ip: int = 0):
        """
        减少资源总配额

        :param service: 接入服务配置对象
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            self.MODEL()

        :raises: QuotaError
        """
        if vcpus < 0 or ram_gib < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
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

            if ram_gib > 0:
                quota.ram_total = max(quota.ram_total - ram_gib, 0)
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

    def requires(self, quota, vcpus: int = 0, ram_gib: int = 0, disk_size: int = 0,
                 public_ip: int = 0, private_ip: int = 0):
        """
        是否满足资源需求，配额默认<=0时不做资源限制

        :param quota: 数据中心资源配额对象
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
        :param disk_size: 硬盘容量，单位Gb
        :param public_ip: 公网ip数
        :param private_ip: 私网ip数
        :return:
            True
            False

        :raises: QuotaError, QuotaShortageError
        """
        if vcpus < 0 or ram_gib < 0 or disk_size < 0 or public_ip < 0 or private_ip < 0:
            raise errors.QuotaError(_('参数无效，扣除资源配额不得小于0'))

        if vcpus > 0 and quota.vcpu_total > 0 and (quota.vcpu_total - quota.vcpu_used) < vcpus:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("vCPU资源配额不足")))

        if ram_gib > 0 and quota.ram_total > 0 and (quota.ram_total - quota.ram_used) < ram_gib:
            raise errors.QuotaShortageError(message=self._prefix_msg(_("Ram资源配额不足")))

        if (
                disk_size > 0 and
                quota.disk_size_total > 0
                and (quota.disk_size_total - quota.disk_size_used) < disk_size
        ):
            raise errors.QuotaShortageError(message=self._prefix_msg(_("Disk资源配额不足")))

        if (
                public_ip > 0 and
                quota.public_ip_total > 0
                and (quota.public_ip_total - quota.public_ip_used) < public_ip
        ):
            raise errors.QuotaShortageError(message=self._prefix_msg(_("公网IP资源配额不足")))

        if (
                private_ip > 0
                and quota.private_ip_total > 0
                and (quota.private_ip_total - quota.private_ip_used) < private_ip
        ):
            raise errors.QuotaShortageError(message=self._prefix_msg(_("私网IP资源配额不足")))

        return True

    def update(self, service, vcpus: int = None, ram_gib: int = None, disk_size: int = None,
               public_ip: int = None, private_ip: int = None, only_increase: bool = True):
        """
        更新资源总配额

        :param service: 接入服务实例
        :param vcpus: 虚拟cpu数
        :param ram_gib: 内存，单位Gb
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

            if ram_gib is not None:
                if only_increase and quota.ram_total > ram_gib:
                    raise errors.QuotaOnlyIncreaseError(message=self._prefix_msg(_('资源配额ram只允许增加')))

                quota.ram_total = max(ram_gib, 0)
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

    def get_privete_queryset(self, center_id: str = None, service_id: str = None):
        qs = self.MODEL.objects.select_related('service').all()

        if service_id:
            qs = qs.filter(service_id=service_id)
        elif center_id:
            qs = qs.filter(service__org_data_center__organization_id=center_id)

        qs = qs.exclude(service__status=ServiceConfig.Status.DELETED.value)
        return qs


class ServiceShareQuotaManager(ServiceQuotaManagerBase):
    """
    接入服务的共享资源配额管理
    """
    MODEL = ServiceShareQuota
    ERROR_MSG_PREFIX = gettext_lazy('服务的共享资源配额')

    def get_share_queryset(self, center_id: str, service_id: str = None):
        qs = self.MODEL.objects.select_related('service').all()
        if service_id:
            qs = qs.filter(service_id=service_id)
        elif center_id:
            qs = qs.filter(service__org_data_center__organization_id=center_id)

        qs = qs.exclude(service__status=ServiceConfig.Status.DELETED.value)
        return qs
