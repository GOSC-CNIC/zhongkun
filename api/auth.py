from collections import namedtuple
from datetime import datetime, timedelta

from onecloud.evcloud.adapter import EVCloudAdapter


AuthClass = namedtuple('AuthClass', ['style', 'token', 'token_head_name', 'expire'])

CACHE_AUTH = {}


def get_adapter(service):
    if service.service_type == service.SERVICE_EVCLOUD:
        return EVCloudAdapter(endpoint_url=service.endpoint_url, api_version=service.api_version)


def get_auth(service, refresh=False):
    """

    :param service:
    :param refresh:
    :return:
    """
    now = datetime.utcnow()
    if not refresh:
        auth = auth_from_cache(service)
        if auth:
            expire = auth.expire
            if now < expire:
                return auth

    adapter = get_adapter(service)

    style, token = adapter.authenticate(username=service.username, password=service.password, style='token')
    auth = AuthClass(style=style, token=token, token_head_name='Token', expire=now + timedelta(hours=1))
    auth_to_cache(service, auth)
    return auth


def auth_to_cache(service, auth):
    CACHE_AUTH[service.id] = auth


def auth_from_cache(service):
    return CACHE_AUTH.get(service.id, None)


def get_auth_header(service):
    auth = get_auth(service)
    if service.service_type == service.SERVICE_EVCLOUD:
        return {'Authorization': f'{auth.token_head_name} {auth.token}'}




