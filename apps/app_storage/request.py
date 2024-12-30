from apps.app_storage.adapter import client as clients
from .adapter.auths import auth_handler
from core import errors


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
    except errors.AuthenticationFailed as exc:
        if raise_exception:
            raise errors.APIException(
                code='Adapter.AuthenticationFailed',
                message='adapter authentication failed', extend_msg=exc.message)

        return None

    raise_exc = errors.APIException()
    for _ in range(2):
        cli = clients.get_service_client(service, auth=auth_obj)
        handler = getattr(cli, method)
        try:
            r = handler(**kwargs)
            if hasattr(r, 'ok'):
                if r.ok:
                    return r

                raise_exc = convert_from_adapter_error(r.error)
                break
            else:
                return r
        except errors.AuthenticationFailed:
            try:
                auth_obj = auth_handler.get_auth(service, refresh=True)
            except errors.AuthenticationFailed as exc:
                raise_exc = errors.APIException(
                    code='Adapter.AuthenticationFailed',
                    message='adapter authentication failed', extend_msg=exc.message)
                break

            continue
        except errors.MethodNotSupportInService as exc:
            raise_exc = errors.MethodNotSupportInService(
                code='Adapter.MethodNotSupportInService',
                message="adapter error:" + exc.message)
            break
        except errors.Error as exc:
            raise_exc = errors.APIException(
                code=f'Adapter.{exc.code}',
                message="adapter error:" + exc.message)
            break
        except Exception as exc:
            raise_exc = errors.APIException(code='Adapter.Error', message=str(exc))
            break

    if raise_exception:
        raise raise_exc

    return None


def convert_from_adapter_error(exc):
    if isinstance(exc, errors.AuthenticationFailed):
        return errors.APIException(
            code='Adapter.AuthenticationFailed',
            message='adapter authentication failed', extend_msg=exc.message)
    # elif isinstance(exc, errors.BucketAlreadyExists):
    #     return exc
    elif isinstance(exc, errors.Error):
        return errors.APIException(code=f'Adapter.{exc.code}', message="adapter error:" + exc.message)

    return errors.APIException(code='Adapter.Error', message=str(exc))
