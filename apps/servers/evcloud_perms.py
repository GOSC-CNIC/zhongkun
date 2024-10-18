from core.adapters import inputs
from core.request import request_service
from apps.servers.models import Server, ServiceConfig
from apps.vo.managers import VoMemberManager


class EVCloudPermsSynchronizer:

    @staticmethod
    def check_need_change_server_owner(server: Server):
        if server.classification != Server.Classification.PERSONAL.value:
            raise Exception('It is not personal server')

        if server.service.service_type != ServiceConfig.ServiceType.EVCLOUD.value:
            raise Exception('The service of server is not EVCloud')

    @staticmethod
    def change_server_owner_to_evcloud(server):
        """
        :raises: Exception
        """
        try:
            EVCloudPermsSynchronizer.check_need_change_server_owner(server)
        except Exception as exc:
            raise exc

        user = server.user
        param = inputs.ServerOwnerChangeInput(instance_id=server.instance_id, new_owner=user.username)
        r = request_service(service=server.service, method='server_owner_change', params=param)
        return r

    @staticmethod
    def check_need_sync_vo_perm(server: Server):
        if server.classification != Server.Classification.VO.value:
            raise Exception('It is not vo server')

        if server.service.service_type != ServiceConfig.ServiceType.EVCLOUD.value:
            raise Exception('The service of server is not EVCloud')

    def sync_vo_server_perms_to_evcloud(self, server):

        try:
            self.check_need_sync_vo_perm(server)
        except Exception as exc:
            raise exc

        perms_map = {}
        service = server.service
        vo = server.vo
        members = VoMemberManager().get_vo_members_queryset(vo_id=vo.id)
        for m in members:
            if m.is_leader_role:
                perm = inputs.ServerSharedUser.READWRITE
            else:
                perm = inputs.ServerSharedUser.READONLY

            username = m.user.username
            perms_map[username] = inputs.ServerSharedUser(username=username, permmison=perm)

        owner_name = vo.owner.username
        perms_map[owner_name] = inputs.ServerSharedUser(
            username=owner_name, permmison=inputs.ServerSharedUser.READWRITE)
        params = inputs.ServerSharedInput(instance_id=server.instance_id, users=list(perms_map.values()))
        r = request_service(service=service, method='server_shared', params=params)
        return r
