from oneservice import exceptions as os_exceptions
from . import auth
from . import exceptions


def get_service_auth_header(service, refresh=False):
    """
    :param service:
    :param refresh:
    :return:
        {}
    :raises: AuthenticationFailed
    """
    t = auth.get_auth(service, refresh=refresh)
    h = t.header
    return {h.header_name: h.header_value}


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
    headers = get_service_auth_header(service)

    client = auth.get_service_client(service)
    handler = getattr(client, method)
    if handler is None:
        raise

    raise_exc = exceptions.APIException()
    for _ in range(2):
        try:
            return handler(headers=headers, **kwargs)
        except os_exceptions.AuthenticationFailed:
            headers = get_service_auth_header(service, refresh=True)
            continue
        except os_exceptions.MethodNotSupportInService as exc:
            raise_exc = exceptions.MethodNotSupportInService(message=exc.message)
            break
        except os_exceptions.Error as exc:
            raise_exc = exceptions.APIException(message=exc.message)
            break

    if raise_exception:
        raise raise_exc

    return None

