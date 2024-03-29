class BaseConfig:
    style: str = None
    endpoint_url: str = None
    region: str = None
    api_version: str = None
    username: str = None
    password: str = None


class EVCloudConfig(BaseConfig):
    pass


class VMwareConfig(BaseConfig):
    pass


class OpenStackConfig(BaseConfig):
    project_name: str = 'admin'
    user_domain: str = 'default'
    project_domain: str = 'default'

