from adapters import exceptions as os_exceptions
from core.auth import auth_handler
from core import client as clients
from . import exceptions


def request_service(service, method: str, raise_exception=True, **kwargs):
    """
    向服务发送请求

    :param service: 接入的服务配置对象
    :param method:
    :param raise_exception: 请求失败是否抛出错误，默认True抛出错误，False返回None
    :param kwargs:
    :return:

    :raises: APIException, AuthenticationFailed
    """
    auth_obj = auth_handler.get_auth(service)
    raise_exc = exceptions.APIException()
    for _ in range(2):
        cli = clients.get_service_client(service, auth=auth_obj)
        handler = getattr(cli, method)
        try:
            r = handler(**kwargs)
            if hasattr(r, 'ok'):
                if r.ok:
                    return r
                raise r.error
            else:
                return r
        except os_exceptions.AuthenticationFailed:
            auth_obj = auth_handler.get_auth(service, refresh=True)
            continue
        except os_exceptions.MethodNotSupportInService as exc:
            raise_exc = exceptions.MethodNotSupportInService(message=exc.message)
            break
        except os_exceptions.Error as exc:
            raise_exc = exceptions.APIException(message=exc.message)
            break

    if raise_exception:
        raise raise_exc


def request_vpn_service(service, method: str, raise_exception=True, **kwargs):
    """
    向VPN服务发送请求

    :param service: 接入的服务配置对象
    :param method:
    :param raise_exception: 请求失败是否抛出错误，默认True抛出错误，False返回None
    :param kwargs:
    :return:

    :raises: APIException, AuthenticationFailed
    """
    auth_obj = auth_handler.get_vpn_auth(service)
    raise_exc = exceptions.APIException()
    for _ in range(2):
        cli = clients.get_service_vpn_client(service, auth=auth_obj)
        handler = getattr(cli, method)
        try:
            r = handler(**kwargs)
            if hasattr(r, 'ok'):
                if r.ok:
                    return r
                raise r.error
            else:
                return r
        except os_exceptions.AuthenticationFailed:
            auth_obj = auth_handler.get_vpn_auth(service, refresh=True)
            continue
        except os_exceptions.MethodNotSupportInService as exc:
            raise_exc = exceptions.MethodNotSupportInService(message=exc.message)
            break
        except os_exceptions.Error as exc:
            raise_exc = exceptions.APIException(message=exc.message)
            break

    if raise_exception:
        raise raise_exc

