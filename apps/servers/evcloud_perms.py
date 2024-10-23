from typing import List

from django.utils import timezone as dj_timezone

from core.adapters import inputs
from core.request import request_service
from core.taskqueue import submit_task
from apps.servers.models import Server, ServiceConfig, EVCloudPermsLog
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

    @staticmethod
    def get_evcloud_servers_of_vo(vo_id):
        servers = Server.objects.select_related('service', 'user', 'vo').filter(
            vo_id=vo_id, classification=Server.Classification.VO,
            service__service_type=ServiceConfig.ServiceType.EVCLOUD.value
        )
        return list(servers)

    def task_sync_servers_perm_to_evcloud(self, servers: List[Server]):
        for server in servers:
            try:
                self.check_need_sync_vo_perm(server)
            except Exception as exc:
                continue

            try:
                self.sync_vo_server_perms_to_evcloud(server=server)
            except Exception as exc:
                # 同步失败记录
                self.create_evcloud_perm_log(server=server, remarks=str(exc))

    def do_when_vo_member_change(self, vo_id):
        servers = self.get_evcloud_servers_of_vo(vo_id=vo_id)
        if servers:
            submit_task(self.task_sync_servers_perm_to_evcloud, kwargs={'servers': servers})

    def do_when_evcloud_server_create(self, servers: List[Server]):
        """
        vo的evcloud云主机创建交付后，需要同步vo组员权限到evcloud云主机的共享用户
        """
        valid_servers = []
        for server in servers:
            try:
                self.check_need_sync_vo_perm(server)
                valid_servers.append(server)
            except Exception as exc:
                continue

        if not valid_servers:
            return

        submit_task(self.task_sync_servers_perm_to_evcloud, kwargs={'servers': valid_servers})

    @staticmethod
    def create_evcloud_perm_log(server: Server, remarks: str = ''):
        nt = dj_timezone.now()
        ins = EVCloudPermsLog(
            server=server, status=EVCloudPermsLog.Status.FAILED.value, num=1,
            creation_time=nt, update_time=nt, remarks=remarks
        )
        ins.save(force_insert=True)
        return ins
