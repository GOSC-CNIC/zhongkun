from datetime import datetime

from adapters import client
from adapters import exceptions as os_exceptions

from . import exceptions


CACHE_AUTH = {}


def get_service_client(service):
    style = client.SERVICE_TYPE_EVCLOUD
    if service.service_type == service.SERVICE_OPENSTACK:
        style = client.SERVICE_TYPE_OPENSTACK

    return client.OneServiceClient(style=style, endpoint_url=service.endpoint_url, api_version=service.api_version)


def get_auth(service, refresh=False):
    """

    :param service:
    :param refresh:
    :return:

    :raises: AuthenticationFailed
    """
    now = datetime.utcnow().timestamp()
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
        auth = s_client.authenticate(username=service.username, password=service.password)
    except os_exceptions.AuthenticationFailed:
        raise exceptions.AuthenticationFailed()

    auth_to_cache(service, auth)
    return auth


def auth_to_cache(service, auth):
    CACHE_AUTH[service.id] = auth


def auth_from_cache(service):
    return CACHE_AUTH.get(service.id, None)


def auth_delete_from_cache(service):
    CACHE_AUTH.pop(service.id, None)

