from service.models import ServiceConfig
from adapters import exceptions
from . import client


class InvalidServiceError(exceptions.Error):
    pass


class InvalidServiceVPNError(exceptions.Error):
    pass


def test_service_ok(service: ServiceConfig):
    """
    检测一下service配置是否有效、可用
    :param service:
    :return:
        True

    :raises: InvalidServiceError, InvalidServiceVPNError
    """
    cli = client.get_service_client(service=service)
    r = cli.authenticate(username=service.username, password=service.password)
    if not r.ok:
        return InvalidServiceError(message=r.error.message, code=r.error.code, status_code=r.error.status_code)

    if not service.is_need_vpn():
        return True

    cli = client.get_service_vpn_client(service=service)
    r = cli.authenticate(username=service.username, password=service.password)
    if not r.ok:
        err = r.error
        return InvalidServiceVPNError(message=err.message, code=err.code, status_code=err.status_code)

    return True
