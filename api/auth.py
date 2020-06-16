from collections import namedtuple
from datetime import datetime, timedelta

from oneservice import client
from oneservice import exceptions as os_exceptions

from . import exceptions


AuthClass = namedtuple('AuthClass', ['style', 'token', 'token_head_name', 'expire'])

CACHE_AUTH = {}


def get_adapter(service):
    style = 'evcloud'
    if service.service_type == service.SERVICE_OPENSTACK:
        style = 'openstack'

    adapter_class = client.get_adapter_class(style)
    return adapter_class(endpoint_url=service.endpoint_url, api_version=service.api_version)


def get_service_client(service):
    return client.OneServiceClient(adapter=get_adapter(service))


def get_auth(service, refresh=False):
    """

    :param service:
    :param refresh:
    :return:

    :raises: AuthenticationFailed
    """
    now = datetime.utcnow()
    if refresh:
        auth_delete_from_cache(service)
    else:
        auth = auth_from_cache(service)
        if auth:
            expire = auth.expire
            if now < expire:
                return auth

    s_client = get_service_client(service)

    try:
        style, token = s_client.authenticate(username=service.username, password=service.password, style='token')
    except os_exceptions.AuthenticationFailed:
        raise exceptions.AuthenticationFailed()

    auth = AuthClass(style=style, token=token, token_head_name='Token', expire=now + timedelta(hours=1))
    auth_to_cache(service, auth)
    return auth


def auth_to_cache(service, auth):
    CACHE_AUTH[service.id] = auth


def auth_from_cache(service):
    return CACHE_AUTH.get(service.id, None)


def auth_delete_from_cache(service):
    CACHE_AUTH.pop(service.id, None)

