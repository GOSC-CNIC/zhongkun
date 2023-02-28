from service.models import ServiceConfig
from adapters import exceptions, client, inputs


class InvalidServiceError(exceptions.Error):
    pass


class InvalidServiceVPNError(InvalidServiceError):
    pass


class AuthenticationFailed(InvalidServiceError):
    pass


class VpnAuthenticationFailed(InvalidServiceError):
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
    params = inputs.AuthenticateInput(username=service.username, password=service.raw_password())
    r = cli.authenticate(params=params)
    if not r.ok:
        raise AuthenticationFailed(message=f'测试认证错误，用户名、密码或服务地址有误，{r.error.message}',
                                   code=r.error.code, status_code=r.error.status_code)

    params = inputs.ListImageInput(region_id=service.region_id, page_num=1, page_size=6)
    r = cli.list_images(params=params)
    if not r.ok:
        raise InvalidServiceError(message=f'测试列举系统镜像失败，{r.error.message}',
                                   code=r.error.code, status_code=r.error.status_code)

    params = inputs.ListNetworkInput(region_id=service.region_id)
    r = cli.list_networks(params=params)
    if not r.ok:
        raise InvalidServiceError(message=f'测试列举网络失败，{r.error.message}',
                                   code=r.error.code, status_code=r.error.status_code)

    if service.is_need_vpn():
        if service.service_type == service.ServiceType.EVCLOUD:
            params = inputs.AuthenticateInput(username=service.username, password=service.raw_password())
        else:
            params = inputs.AuthenticateInput(username=service.vpn_username, password=service.raw_vpn_password())

        cli = client.get_service_vpn_client(service=service)
        r = cli.authenticate(params=params)
        if not r.ok:
            err = r.error
            raise VpnAuthenticationFailed(message=f'测试vpn认证错误，用户名、密码或服务地址有误，{err.message}',
                                          code=err.code, status_code=err.status_code)

        r = cli.get_vpn_or_create(username='test')
        if 'username' not in r or 'password' not in r:
            raise VpnAuthenticationFailed(message='查询或创建vpn账户失败')

    return True
