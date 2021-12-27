from django.utils.translation import gettext as _
from django.db.models import Subquery

from core import errors
from vo.managers import VoManager
from .models import Server, ServerArchive


class ServerManager:
    @staticmethod
    def get_server_queryset():
        return Server.objects.all()

    def get_user_servers_queryset(self, user, service_id: str = None, ipv4_contains: str = None):
        """
        查询用户个人server
        """
        lookups = {}
        if ipv4_contains:
            lookups['ipv4__contains'] = ipv4_contains

        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user_quota', 'user').filter(
            user=user, classification=Server.Classification.PERSONAL, **lookups)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def get_admin_servers_queryset(self, user, service_id: str = None, user_id: str = None, username: str = None,
                                   vo_id: str = None, ipv4_contains: str = None):
        """
        管理员查询server

        :raises: Error
        """
        if (user_id or username) and vo_id:
            return self.get_server_queryset().none()

        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user_quota', 'user')

        if user_id or username:
            lookups = {'classification': Server.Classification.PERSONAL}
            if user_id:
                lookups['user_id'] = user_id
            if username:
                lookups['user__username'] = username
            qs = qs.filter(**lookups)
        elif vo_id:
            qs = qs.filter(vo_id=vo_id, classification=Server.Classification.VO)

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

        if ipv4_contains:
            qs = qs.filter(ipv4__contains=ipv4_contains)

        return qs

    def get_vo_servers_queryset(self, vo_id: str, service_id: str = None):
        """
        查询vo组的server
        """
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user_quota', 'user').filter(
            vo_id=vo_id, classification=Server.Classification.VO)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    @staticmethod
    def get_server(server_id: str, related_fields: list = None) -> Server:
        fields = ['service', 'user_quota', 'user']
        if related_fields:
            for f in related_fields:
                if f not in fields:
                    fields.append(f)

        server = Server.objects.filter(id=server_id).select_related(*fields).first()
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


class ServerArchiveManager:
    @staticmethod
    def get_archives_queryset():
        return ServerArchive.objects.all()

    def get_user_archives_queryset(self, user, service_id: str = None):
        """
        查询用户个人server归档记录
        """
        qs = self.get_archives_queryset()
        qs = qs.select_related('service', 'user_quota').filter(
            user=user, classification=ServerArchive.Classification.PERSONAL)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def get_vo_archives_queryset(self, vo_id: str, service_id: str = None):
        """
        查询vo组的server归档记录
        """
        qs = self.get_archives_queryset()
        qs = qs.select_related('service', 'user_quota').filter(
            vo_id=vo_id, classification=ServerArchive.Classification.VO)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs
