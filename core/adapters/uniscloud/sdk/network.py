from .model import Request, build_url


class NetworkBase:
    Location = '/networks'

    def __init__(self, endpoint_url: str, region_id: str, signer):
        self.endpoint_url = endpoint_url
        self.region_id = region_id
        self.signer = signer

    def _build_request(self, method: str, params):
        api = build_url(self.endpoint_url, self.Location)
        return Request(
            method=method,
            url=api,
            params=params
        )


class VPC(NetworkBase):
    Location = '/networks/vpc'

    def list(self):
        """
        """
        params = {
            'Action': 'DescribeVpc',
            'RegionId': self.region_id
        }
        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)

    def list_subnet(self, vpc_id: str):
        """
        """
        params = {
            'Action': 'DescribeSubnet',
            'RegionId': self.region_id,
            'VpcId': vpc_id
        }
        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)


class SecurityGroup(NetworkBase):
    Location = '/networks/securitygroup'

    def list(self):
        """
        """
        params = {
            'Action': 'DescribeSecurityGroup',
            'RegionId': self.region_id
        }
        request = self._build_request(method='GET', params=params)
        return request.do_request(self.signer)


class Network(NetworkBase):
    @property
    def vpc(self):
        return VPC(endpoint_url=self.endpoint_url, region_id=self.region_id, signer=self.signer)

    @property
    def security_group(self):
        return SecurityGroup(endpoint_url=self.endpoint_url, region_id=self.region_id, signer=self.signer)
