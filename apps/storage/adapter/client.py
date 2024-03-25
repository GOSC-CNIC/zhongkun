from storage.models import ObjectsService

from .iharbor import IHarborClient


def get_service_client(service: ObjectsService, **kwargs):
    params = {}
    auth = kwargs.pop('auth') if 'auth' in kwargs else None
    params.update(kwargs)
    return IHarborClient(
        endpoint_url=service.endpoint_url, api_version=service.api_version,
        auth=auth, **params
    )
