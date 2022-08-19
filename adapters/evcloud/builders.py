from urllib import parse

from . import exceptions


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


def replace_query_param(url, key, val):
    """
    Given a URL and a key/val pair, set or replace an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[key] = [val]
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


def remove_query_param(url, key):
    """
    Given a URL and a key/val pair, remove an item in the query
    parameters of the URL, and return the new URL.
    """
    (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict.pop(key, None)
    query = parse.urlencode(sorted(list(query_dict.items())), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


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

    def token_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/token', query=query)

    def jwt_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/jwt', query=query)

    def image_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/image', query=query)

    def image_detail_url(self, image_id: int, query=None):
        return self.build_url(path=f'api/{self.api_version}/image/{image_id}/', query=query)

    def vm_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms', query=query)

    def vm_detail_url(self, vm_uuid: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms/{vm_uuid}', query=query)

    def vm_action_url(self, vm_uuid: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms/{vm_uuid}/operations/', query=query)

    def vm_status_url(self, vm_uuid: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms/{vm_uuid}/status/', query=query)

    def vm_vnc_url(self, vm_uuid: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms/{vm_uuid}/vnc/', query=query)

    def vm_reset_url(self, vm_uuid: str, image_id: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vms/{vm_uuid}/reset/{image_id}/', query=query)

    def vlan_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/vlan/', query=query)

    def vlan_detail_url(self, pk, query=None):
        return self.build_url(path=f'api/{self.api_version}/vlan/{pk}/', query=query)

    def group_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/group/', query=query)

    def flavor_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/flavor/', query=query)

    def flavor_detail_url(self, pk, query=None):
        return self.build_url(path=f'api/{self.api_version}/flavor/{pk}/', query=query)

    def vpn_base_url(self, query=None):
        return self.build_url(path=f'api/{self.api_version}/vpn/', query=query)

    def vpn_detail_url(self, username: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vpn/{username}/', query=query)

    def vpn_config_file_url(self):
        return self.build_url(path=f'vpn/vpnfile/config', trailing_slash=False)

    def vpn_ca_file_url(self):
        return self.build_url(path=f'vpn/vpnfile/ca', trailing_slash=False)

    def vpn_active_url(self, username: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vpn/{username}/active/', query=query)

    def vpn_deactive_url(self, username: str, query=None):
        return self.build_url(path=f'api/{self.api_version}/vpn/{username}/deactive/', query=query)
