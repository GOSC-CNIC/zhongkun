from django.utils.translation import gettext as _

from core import errors
from vo.managers import VoManager
from .models import Server


class ServerManager:
    @staticmethod
    def get_server_queryset():
        return Server.objects.all()

    def get_user_servers_queryset(self, user, service_id: str = None):
        """
        查询用户个人server
        """
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user_quota').filter(
            user=user, classification=Server.Classification.PERSONAL)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def get_vo_servers_queryset(self, vo_id: str, service_id: str = None):
        """
        查询vo组的server
        """
        qs = self.get_server_queryset()
        qs = qs.select_related('service', 'user_quota').filter(
            vo_id=vo_id, classification=Server.Classification.VO)

        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    @staticmethod
    def get_server(server_id: str, related_fields: list = None) -> Server:
        fields = ['service', 'user_quota']
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

    def get_manage_perm_server(self, server_id: str, user, related_fields: list = None) -> Server:
        """
        查询用户有管理权限的虚拟服务器实例
        :raises: Error
        """
        return self.get_permission_server(server_id=server_id, user=user, related_fields=related_fields,
                                          read_only=False)

    def get_read_perm_server(self, server_id: str, user, related_fields: list = None) -> Server:
        """
        查询用户有访问权限的虚拟服务器实例
        :raises: Error
        """
        return self.get_permission_server(server_id=server_id, user=user, related_fields=related_fields,
                                          read_only=True)


