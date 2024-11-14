from datetime import timedelta

import requests
from django.utils import timezone as dj_timezone

from core import errors
from apps.service.models import KunYuanService


class KunYuanServiceManager:
    @staticmethod
    def get_kunyuan_version(service: KunYuanService):
        endpoint_url = service.endpoint_url.rstrip('/')
        api_url = f'{endpoint_url}/api/version'
        r = requests.get(url=api_url)
        if r.status_code == 200:
            data = r.json()
            version = data['version']
            return version

        raise errors.Error(message=r.text)

    @staticmethod
    def update_service_version(service: KunYuanService):
        try:
            nt = dj_timezone.now()
            if not service.version_update_time or (nt - service.version_update_time) > timedelta(minutes=1):
                version = KunYuanServiceManager.get_kunyuan_version(service=service)
                if version:
                    service.version = version
                    service.version_update_time = nt
                    service.save(update_fields=['version', 'version_update_time'])
        except Exception as exc:
            return exc

        return True
