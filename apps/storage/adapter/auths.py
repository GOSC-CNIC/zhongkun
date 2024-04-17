from datetime import datetime
from threading import local

from apps.storage.adapter import inputs, client
from apps.storage.models import ObjectsService
from core import errors


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

    def get_auth(self, service: ObjectsService, refresh=False):
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
            password = service.raw_password
            if password is None:
                raise errors.AuthenticationFailed(f'Invalid password of service "{str(service)}"')

            params = inputs.AuthenticateInput(username=service.username, password=password)
            auth = s_client.authenticate(params)
            if not auth.ok:
                raise errors.AuthenticationFailed(
                    f'Authentication failed to service "{str(service)}", error: {str(auth.error)}')
        except errors.AuthenticationFailed as exc:
            raise errors.AuthenticationFailed(
                f'Authentication failed to service "{str(service)}", error: {str(exc)}')

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


auth_handler = AuthCacheHandler()
