from core.adapters import inputs
from core.request import request_service
from apps.servers.models import Server, ServiceConfig


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
