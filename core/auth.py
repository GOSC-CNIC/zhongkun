from datetime import datetime
from threading import local

from adapters import exceptions as os_exceptions, client
from adapters import inputs
from servers.models import ServiceConfig
from . import errors as exceptions


class AuthCacheHandler:
    def __init__(self):
        self._auths = local()

    def __getitem__(self, key):
        if hasattr(self._auths, key):
            return getattr(self._auths, key)

        return None

    def __setitem__(self, key, value):
        setattr(self._auths, key, value)

    def __delitem__(self, key):
        delattr(self._auths, key)

    def get_auth(self, service: ServiceConfig, refresh=False):
        """
        获取身份认证信息

        :param service:
        :param refresh:
        :return:

        :raises: AuthenticationFailed
        """
        now = datetime.utcnow().timestamp()
        key = self.get_service_key(service)

        if refresh:
            del self[key]
        else:
            auth = self[key]
            if auth:
                expire = auth.expire
                if now < expire:
                    return auth

        s_client = client.get_service_client(service)
        try:
            password = service.raw_password()
            if password is None:
                raise exceptions.AuthenticationFailed(f'Invalid password of service "{str(service)}"')

            params = inputs.AuthenticateInput(username=service.username, password=password)
            auth = s_client.authenticate(params)
            if not auth.ok:
                raise exceptions.AuthenticationFailed(
                    f'Authentication failed to service "{str(service)}", error: {str(auth.error)}')
        except os_exceptions.AuthenticationFailed as exc:
            raise exceptions.AuthenticationFailed(
                f'Authentication failed to service "{str(service)}", error: {str(exc)}')

        self[key] = auth
        return auth

    def get_vpn_auth(self, service: ServiceConfig, refresh=False):
        if service.service_type == service.ServiceType.EVCLOUD:
            return self.get_auth(service=service, refresh=refresh)

        now = datetime.utcnow().timestamp()
        key = self.get_service_vpn_key(service)

        if refresh:
            del self[key]
        else:
            auth = self[key]
            if auth:
                expire = auth.expire
                if now < expire:
                    return auth

        cli = client.get_service_vpn_client(service)
        try:
            vpn_password = service.raw_vpn_password()
            if vpn_password is None:
                raise exceptions.AuthenticationFailed(f'Invalid vpn_password of service "{str(service)}"')

            params = inputs.AuthenticateInput(username=service.vpn_username, password=vpn_password)
            auth = cli.authenticate(params)
            if not auth.ok:
                raise exceptions.AuthenticationFailed(f'Authentication failed to vpn of service "{str(service)}"')
        except os_exceptions.AuthenticationFailed:
            raise exceptions.AuthenticationFailed(f'Authentication failed to vpn of service "{str(service)}"')

        self[key] = auth
        return auth

    def auth_to_cache(self, service, auth):
        key = self.get_service_key(service)
        self[key] = auth

    def auth_from_cache(self, service):
        key = self.get_service_key(service)
        return self[key]

    def auth_delete_from_cache(self, service):
        delattr(self._auths, service.id)

    @staticmethod
    def get_service_key(service):
        return f'service_{service.id}'

    @staticmethod
    def get_service_vpn_key(service):
        return f'vpn_{service.id}'


auth_handler = AuthCacheHandler()
