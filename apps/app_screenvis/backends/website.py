from urllib import parse
from string import Template

import requests

from apps.app_screenvis.utils import errors


class WebsiteExpressionQuery:
    duration_seconds = 'probe_duration_seconds'
    tmpl_duration_seconds = 'probe_duration_seconds{url="$url"}'
    http_duration_seconds = 'probe_http_duration_seconds'
    tmpl_http_duration_seconds = 'probe_http_duration_seconds{url="$url"}'

    @staticmethod
    def render_expression(tmpl: str, url: str = None):
        expression_query = tmpl
        if url:
            expression_query = Template(tmpl).substitute(url=url)

        return expression_query


class WebMonitorQueryAPI:
    @staticmethod
    def request_query_api(url: str):
        """
        :raises: Error
        """
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='backend query api request timeout')
        except requests.exceptions.RequestException as exc:
            raise errors.Error(message=f'backend query api request error: {str(exc)}')

        data = r.json()
        if 300 > r.status_code >= 200:
            s = data.get('status')
            if s == 'success':
                return data['data']['result']

        raise WebMonitorQueryAPI._build_error(r)

    @staticmethod
    def _build_error(r):
        data = r.json()
        msg = f"status: {r.status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        return errors.Error(message=msg)

    @staticmethod
    def _build_query_url(endpoint_url: str, querys: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=querys)
        return f'{endpoint_url}/api/v1/query?{query}'

    @staticmethod
    def raw_query(endpoint_url: str, querys: dict):
        api_url = WebMonitorQueryAPI._build_query_url(endpoint_url=endpoint_url, querys=querys)
        return WebMonitorQueryAPI.request_query_api(url=api_url)
