from urllib import parse


def enforce_query(query):
    """
    强制为query字符串

    :param query: None or str or dict
    :return:
        str
    """
    if isinstance(query, dict):
        query_str = parse.urlencode(sorted(list(query.items())), doseq=True)
    elif isinstance(query, str):
        query_str = query
    else:
        query_str = ''

    return query_str


class APIBuilder:
    """
    API url builder
    """
    def __init__(self, endpoint_url: str, api_version: str, **kwargs):
        self.endpoint_url = endpoint_url
        self.api_version = api_version
        self.extra_kwargs = kwargs

    def build_url(self, endpoint_url: str = '', path: str = '', query=None, fragment: str = '', trailing_slash=True):
        """
        构建url

        :param endpoint_url: 默认self.endpoint_url
        :param path:
        :param query: type: str or dict;
        :param fragment:
        :param trailing_slash: 默认True，path后尾随/；
        :return:
        """
        query_str = enforce_query(query)

        if trailing_slash and not path.endswith('/'):
            path += '/'
        elif not trailing_slash and path.endswith('/'):
            path = path.rstrip('/')

        endpoint_url = endpoint_url if endpoint_url else self.endpoint_url
        scheme, netloc, _, _, _ = parse.urlsplit(endpoint_url)
        return parse.urlunsplit((scheme, netloc, path, query_str, fragment))

    def jwt_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/jwt', query=query)

    def bucket_lock_url(self, bucket_name: str, lock: str, query=None):
        return self.build_url(
            path=f'api/{self.api_version}/admin/bucket/{bucket_name}/lock/{lock}',
            query=query, trailing_slash=False
        )

    def bucket_create_url(self, query=None):
        return self.build_url(
            path=f'api/{self.api_version}/admin/bucket',
            query=query, trailing_slash=False
        )

    def bucket_delete_url(self, bucket_name: str, username: str, query=None):
        return self.build_url(
            path=f'api/{self.api_version}/admin/bucket/{bucket_name}/user/{username}',
            query=query, trailing_slash=False
        )

    def bucket_stats_url(self, bucket_name: str, query=None):
        return self.build_url(
            path=f'api/{self.api_version}/stats/bucket/{bucket_name}',
            query=query, trailing_slash=True
        )

    def version_url(self):
        return self.build_url(
            path=f'api/{self.api_version}/version',
            query=None, trailing_slash=True
        )
