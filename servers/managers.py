from decimal import Decimal

from django.utils.translation import gettext as _
from django.db.models import Subquery, Q
from django.utils import timezone

from core import errors
from vo.managers import VoManager
from bill.managers import PaymentManager
from utils.model import PayType
from .models import Server, ServerArchive, Flavor
from .server_instance import ServerInstance


class ServerManager:
    @staticmethod
    def get_server_queryset():
        return Server.objects.all()

    def get_user_servers_queryset(self, user, service_id: str = None, ipv4_contains: str = None, expired: bool = None):
        """
        查询用户个人server

        :param user: 用户过滤
        :param service_id: 服务单元id过滤
        :param ipv4_contains: ip包含过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :return: QuerySet()
        """
        lookups = {}
        if ipv4_contains:
            lookups['ipv4__contains'] = ipv4_contains

        if service_id:
            lookups['service_id'] = service_id

        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user').filter(
            user=user, classification=Server.Classification.PERSONAL, **lookups)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))     # 取反的方式，存在expiration_time == None

        return qs

    def get_admin_servers_queryset(
            self, user, service_id: str = None, ipv4_contains: str = None, expired: bool = None,
            vo_id: str = None, vo_name: str = None, user_id: str = None, username: str = None,
            exclude_vo: bool = None
    ):
        """
        管理员查询server

        :param user: 管理员用户
        :param service_id: 服务单元id过滤
        :param user_id: 过滤用户, 包括vo内的用户创建的
        :param username: 过滤用户名,模糊查询, 包括vo内的用户创建的
        :prram vo_id: 过滤vo
        :param ipv4_contains: ip包含过滤
        :param expired: True(过期过滤)；False(未过期过滤)：默认None不过滤
        :param vo_name: 过滤vo组名,模糊查询
        :param exclude_vo: True(排除vo组的server)，其他忽略
        :return: QuerySet()
        :raises: Error
        """
        if (user_id or username) and vo_id:
            return self.get_server_queryset().none()

        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user')

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
                qs = qs.filter(service_id=service_id)
        else:
            if service_id:
                service = user.service_set.filter(id=service_id).first()
                if service is None:
                    raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

                qs = qs.filter(service_id=service_id)
            else:
                subq = Subquery(user.service_set.all().values_list('id', flat=True))
                qs = qs.filter(service_id__in=subq)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))

        if ipv4_contains:
            qs = qs.filter(ipv4__contains=ipv4_contains)

        return qs

    def get_vo_servers_queryset(self, vo_id: str, service_id: str = None, expired: bool = None):
        """
        查询vo组的server
        """
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user').filter(
            vo_id=vo_id, classification=Server.Classification.VO)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if expired is True:
            qs = qs.filter(expiration_time__lte=timezone.now())
        elif expired is False:
            qs = qs.filter(~Q(expiration_time__lte=timezone.now()))

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
        elif server.service.user_has_perm(user):
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
            elif not server.service.pay_app_service_id:
                raise errors.ArrearageSuspending(
                    message=_('云主机欠费停机停服挂起中，云主机所属服务没有配置余额结算系统app服务id，无法查询用户或vo组是否还欠费'))

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
            if ok:
                server.set_situation_normal()
            else:
                raise errors.ArrearageSuspending(message=_('云主机欠费停机停服挂起中'))
        else:
            raise errors.ConflictError(message=_('云主机管控状态未知'))

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
        self.do_suspend_server(server=server,situation=Server.Situation.NORMAL.value)

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
    def get_enable_flavor(self, _id):
        return Flavor.objects.filter(id=_id, enable=True).first()
