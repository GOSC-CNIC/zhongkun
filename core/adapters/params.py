class BaseAdapterParams:
    """
    适配器需要的额外的自定义参数
    """
    REGION = 'region'

    def get_custom_params(self) -> dict:
        """
        返回适配器自定义参数
        :return: {
            key     # 参数名称
            value   # 参数描述
        }
        """
        raise NotImplemented()


class GenericAdapterParams(BaseAdapterParams):
    """
    通用的，无特殊自定义参数需求适配器使用
    """
    def get_custom_params(self):
        return {}


class OpenStackParams(BaseAdapterParams):
    PROJECT_NAME = 'project_name'
    PROJECT_DOMAIN_NAME = 'project_domain_name'
    USER_DOMAIN_NAME = 'user_domain_name'

    custom_params = (
        (PROJECT_NAME, '项目名称'),
        (PROJECT_DOMAIN_NAME, '项目域名称'),
        (USER_DOMAIN_NAME, '用户域名称')
    )

    def get_custom_params(self) -> dict:
        return {k: v for k, v in self.custom_params}
