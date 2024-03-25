from .model import Request, build_url


class RegionBase:
    Location = '/'

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


class Product(RegionBase):
    Location = '/product'

    def get_user_quota(self, region_id: str, is_trial: bool = True):
        """
        :params is_trial: True(查询试用配额)，False(查询用户所有正式配额)
        """
        params = {
            'Action': 'GetUserAllQuota',
            'RegionId': region_id,
            'IsTrial': is_trial
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def get_region(self, product_code: str):
        """
        查询紫光云产品可用地域信息
        """
        params = {
            'Action': 'GetRegion',
            'ProductCode': product_code
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)


class UserRegion(RegionBase):
    Location = '/user/user'

    def list_user_region(self):
        params = {
            'Action': 'ListUserRegion'
        }

        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)
