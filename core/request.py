from adapters import exceptions as apt_exceptions, client as clients
from adapters import inputs, outputs
from .auth import auth_handler
from . import errors as exceptions


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


def update_server_detail(server, task_status: int = None):
    """
    尝试更新服务器的详细信息
    :param server:
    :param task_status: 设置server的创建状态；默认None忽略
    :return:
        Server    # success
        raise Error   # failed

    :raises: Error
    """
    # 尝试获取详细信息
    params = inputs.ServerDetailInput(instance_id=server.instance_id, instance_name=server.instance_name)
    try:
        out = request_service(service=server.service, method='server_detail', params=params)
        out_server = out.server
    except exceptions.APIException as exc:      #
        raise exc

    try:
        update_fields = []

        if not server.name:
            server.name = out_server.name if out_server.name else out_server.uuid
            update_fields.append('name')

        if not server.instance_id:
            if out_server.uuid:
                server.instance_id = out_server.uuid
                update_fields.append('instance_id')

        if not server.instance_name:
            if out_server.name:
                server.instance_name = out_server.name
                update_fields.append('instance_name')

        if out_server.vcpu:
            server.vcpus = out_server.vcpu
            update_fields.append('vcpus')

        if out_server.ram:
            server.ram = out_server.ram
            update_fields.append('ram')

        is_public_ipv4 = out_server.ip.public_ipv4
        if is_public_ipv4 is not None:
            server.public_ip = is_public_ipv4
            update_fields.append('public_ip')

        ipv4 = out_server.ip.ipv4
        if ipv4:
            server.ipv4 = ipv4
            update_fields.append('ipv4')

        image = out_server.image.name
        if image:
            server.image = image
            update_fields.append('image')

        image_desc = out_server.image.desc
        if image_desc:
            server.image_desc = image_desc
            update_fields.append('image_desc')

        default_user = out_server.default_user
        if default_user:
            server.default_user = default_user
            update_fields.append('default_user')

        default_password = out_server.default_password
        if default_password:
            server.raw_default_password = default_password
            update_fields.append('default_password')

        if task_status:
            if server.ipv4 and server.image:
                server.task_status = task_status
                update_fields.append('task_status')

        if out_server.azone_id:
            server.azone_id = out_server.azone_id
            update_fields.append('azone_id')

        if update_fields:
            server.save(update_fields=update_fields)
    except Exception as e:
        raise exceptions.APIException(message=str(e))

    return server


def server_status_code(server):
    """
    查询云服务器的状态

    :return:
        (code: int, mean: str)

    :raises: APIException
    """
    params = inputs.ServerStatusInput(instance_id=server.instance_id, instance_name=server.instance_name)
    service = server.service
    try:
        r = request_service(service, method='server_status', params=params)
    except exceptions.APIException as exc:
        raise exc

    return r.status, r.status_mean


def server_build_status(server):
    """
    云服务器创建状态

    :return: str
        "created"       # 创建完成
        "failed"        # 创建失败
        "building"      # 创建中
        "error"         # 查询状态失败
    """
    try:
        status_code, _ = server_status_code(server)
    except Exception as e:
        return "error"

    if status_code in outputs.ServerStatus.normal_values():     # 虚拟服务器状态正常
        return "created"
    elif status_code in [outputs.ServerStatus.MISS, outputs.ServerStatus.BUILT_FAILED, outputs.ServerStatus.ERROR]:
        return "failed"
    else:
        return "building"



