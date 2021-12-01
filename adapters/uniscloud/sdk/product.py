from .model import Request, build_url


class Product:
    Location = '/product'

    def __init__(self, endpoint_url: str, signer):
        self.endpoint_url = endpoint_url
        self.signer = signer

    def _build_request(self, method: str, params):
        api = build_url(self.endpoint_url, self.Location)
        return Request(
            method=method,
            url=api,
            params=params
        )

    def get_user_quota(self, region_id: str):
        params = {
            'Action': 'GetUserAllQuota',
            'RegionId': region_id
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)


class UserRegion:
    Location = '/user/user'

    def __init__(self, endpoint_url: str, signer):
        self.endpoint_url = endpoint_url
        self.signer = signer

    def _build_request(self, method: str, params):
        api = build_url(self.endpoint_url, self.Location)
        return Request(
            method=method,
            url=api,
            params=params
        )

    def list_user_region(self):
        params = {
            'Action': 'ListUserRegion'
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)
