from .auth import Credentials, BaseSigner, SignV1Auth
from .compute import Compute
from .product import Product, UserRegion


class UnisCloud:
    def __init__(self,
                 credentials: Credentials,
                 endpoint_url: str = 'https://api.unicloud.com/',
                 region_id: str = 'cn-beijing',
                 version: str = '2020-07-30',
                 format: str = 'json',
                 signer: BaseSigner = None
                 ):
        self.credentials = credentials
        self.endpoint_url = endpoint_url
        self.region_id = region_id
        self.version = version
        self.format = format
        if signer is None:
            self.siger = SignV1Auth(self.credentials)
        else:
            self.siger = signer

    @property
    def compute(self):
        return Compute(
            endpoint_url=self.endpoint_url,
            region_id=self.region_id,
            signer=self.siger
        )

    @property
    def product(self):
        return Product(
            endpoint_url=self.endpoint_url,
            signer=self.siger
        )

    @property
    def user_region(self):
        return UserRegion(
            endpoint_url=self.endpoint_url,
            signer=self.siger
        )

    def list_user_region(self):
        return self.user_region.list_user_region()

