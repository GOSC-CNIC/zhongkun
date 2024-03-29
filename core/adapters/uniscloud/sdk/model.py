import json
import requests
from urllib import parse


class BaseError(BaseException):
    def __init__(self, message: str, err=None):
        self.message = message
        self.err = err

    def __str__(self):
        if self.message:
            return self.message

        if self.err:
            return str(self.err)

        return ''


class InvalidURL(BaseError):
    pass


class RequestError(BaseError):
    pass


def build_url(*args):
    items = []
    for p in args:
        items.append(p.strip('/'))

    return '/'.join(items)


class Request:
    def __init__(self, method=None, url=None, headers=None, files=None, data=None,
                 params=None, auth=None, version='2020-07-30', format='json'):
        """
        url not contain query params
        """
        # Default empty dicts for dict params.
        data = [] if data is None else data
        files = [] if files is None else files
        headers = {} if headers is None else headers
        params = {} if params is None else params

        self.method = method
        self.url = url
        self.headers = headers
        self.files = files
        self.data = data
        self.params = params
        self.auth = auth
        self.format = format

        url, querys = self.hand_url(self.url)
        self.url = url
        if querys:
            self.params.update(querys)

        self.add_param("Format", format)
        self.add_param("Version", version)

    def hand_url(self, url: str):
        (scheme, netloc, path, query, fragment) = parse.urlsplit(url)
        query_dict = parse.parse_qs(query, keep_blank_values=True)
        url = parse.urlunsplit((scheme, netloc, path, None, fragment))
        return url, query_dict

    def add_param(self, key: str, val):
        self.params[key] = val

    def do_request(self, signer):
        """
        :return:
            requests.Response

        :raises:
        """
        signer.add_auth(request=self)
        data = self.data
        json_data = None
        if data and self.format == 'json':
            json_data = data
            data = None

        try:
            r = requests.request(
                method=self.method,
                url=self.url,
                headers=self.headers,
                json=json_data,
                data=data,
                files=self.files,
                params=self.params
            )
            return r
        except requests.exceptions.RequestException as e:
            raise RequestError(message=str(e), err=e)
