from adapters import exceptions as apt_exceptions
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

    :raises: APIException
    """
    try:
        auth_obj = auth_handler.get_auth(service)
    except apt_exceptions.AuthenticationFailed as exc:
        if raise_exception:
            raise exceptions.APIException(message='adapter authentication failed', extend_msg=exc.message)
        return None

    raise_exc = exceptions.APIException()
    for _ in range(2):
        cli = clients.get_service_client(service, auth=auth_obj)
        handler = getattr(cli, method)
        try:
            r = handler(**kwargs)
            if hasattr(r, 'ok'):
                if r.ok:
                    return r

                raise_exc = exceptions.APIException(message='adapter error:' + r.error.message)
                break
            else:
                return r
        except apt_exceptions.AuthenticationFailed:
            try:
                auth_obj = auth_handler.get_auth(service, refresh=True)
            except apt_exceptions.AuthenticationFailed as exc:
                raise_exc = exceptions.APIException(message='adapter authentication failed', extend_msg=exc.message)
                break

            continue
        except apt_exceptions.MethodNotSupportInService as exc:
            raise_exc = exceptions.MethodNotSupportInService(message="adapter error:" + exc.message)
            break
        except apt_exceptions.ServerNotExist as exc:
            raise_exc = exceptions.ServerNotExist(message=exc.message)
        except apt_exceptions.Error as exc:
            raise_exc = exceptions.APIException(message="adapter error:" + exc.message)
            break
        except Exception as exc:
            raise_exc = exceptions.APIException(message=str(exc))
            break

    if raise_exception:
        raise raise_exc

    return None


def request_vpn_service(service, method: str, raise_exception=True, **kwargs):
    """
    向VPN服务发送请求

    :param service: 接入的服务配置对象
    :param method:
    :param raise_exception: 请求失败是否抛出错误，默认True抛出错误，False返回None
    :param kwargs:
    :return:

    :raises: APIException
    """
    try:
        auth_obj = auth_handler.get_vpn_auth(service)
    except apt_exceptions.AuthenticationFailed as exc:
        if raise_exception:
            raise exceptions.APIException(message='vpn adapter authentication failed', extend_msg=exc.message)

        return None

    raise_exc = exceptions.APIException()
    for _ in range(2):
        cli = clients.get_service_vpn_client(service, auth=auth_obj)
        handler = getattr(cli, method)
        try:
            r = handler(**kwargs)
            if hasattr(r, 'ok'):
                if r.ok:
                    return r

                raise_exc = exceptions.APIException(message='vpn adapter error:' + r.error.message)
                break
            else:
                return r
        except apt_exceptions.AuthenticationFailed:
            try:
                auth_obj = auth_handler.get_vpn_auth(service, refresh=True)
            except apt_exceptions.AuthenticationFailed as exc:
                raise_exc = exceptions.APIException(message='vpn adapter authentication failed', extend_msg=exc.message)
                break

            continue
        except apt_exceptions.MethodNotSupportInService as exc:
            raise_exc = exceptions.MethodNotSupportInService(message=exc.message)
            break
        except apt_exceptions.Error as exc:
            raise_exc = exceptions.APIException(message=exc.message)
            break

    if raise_exception:
        raise raise_exc

    return None
