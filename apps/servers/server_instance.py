from adapters import inputs, outputs
from core import errors
from core.request import request_service
from core import request as core_request


class ServerInstance:
    ServerAction = inputs.ServerAction
    ServerStatus = outputs.ServerStatus

    def __init__(self, server):
        self.server = server

    def action(self, act: str):
        """
        :raises: Error
        """
        server = self.server
        params = inputs.ServerActionInput(
            instance_id=server.instance_id, instance_name=server.instance_name, action=act)

        try:
            r = request_service(server.service, method='server_action', params=params)
        except errors.APIException as exc:
            raise exc

    def status(self):
        """
        :raises: Error
        """
        try:
            status_code, status_text = core_request.server_status_code(server=self.server)
        except errors.APIException as exc:
            raise exc

        return status_code, status_text
