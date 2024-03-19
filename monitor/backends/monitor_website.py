import requests
from urllib import parse

from core import errors
from monitor.models import MonitorProvider


class ExpressionQuery:
    """
    probe_http_status_code{} offset 5m  # 5m前的数据
    """
    http_status_code = 'probe_http_status_code'
    duration_seconds = 'probe_duration_seconds'
    http_duration_seconds = 'probe_http_duration_seconds'

    @staticmethod
    def build_http_status_code_query(url: str):
        return f'probe_http_status_code{{url="{url}"}}'

    @staticmethod
    def build_duration_seconds_query(url: str):
        return f'probe_duration_seconds{{url="{url}"}}'

    @staticmethod
    def build_http_duration_seconds_query(url: str):
        return f'probe_http_duration_seconds{{url="{url}"}}'

    @staticmethod
    def build_success_query(url: str):
        return f'probe_success{{url="{url}"}}'


class MonitorWebsiteQueryAPI:
    """
    response data example:
    [
        {
            'metric': {
                '__name__': 'probe_http_status_code',
                'group': 'web',
                'instance': 'http_status',
                'job': 'http_status',
                'monitor': 'example',
                'receive_cluster': 'webmonitor',
                'receive_replica': '0',
                'tenant_id': 'default-tenant',
                'url': 'http://www.nairc.com/'
            },
            "value": [1630267851.781, "1622079296241664"]       # when query
            "values": [                                         # when query_rang
                [1630267851.781, "1622079296241664"]
            ]
        },
        ...
    ]
    """

    def http_status_code(self, provider: MonitorProvider, url: str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "200"
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_http_status_code_query(url=url)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def http_status_code_period(self, provider: MonitorProvider, url: str):
        """
        [
            {
                'metric': {}
                ,
                'values': [
                    [1675218651.941, '404'],
                    [1675218666.941, '404']
                ]
            }
        ]
        """
        expression_query = ExpressionQuery().build_http_status_code_query(url=url) + '[5m]'
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def duration_seconds(self, provider: MonitorProvider, url: str):
        """
        http or tcp
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        '0.032904559'
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_duration_seconds_query(url=url)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def duration_seconds_period(self, provider: MonitorProvider, url: str):
        """
        http or tcp
        [
            {
                'metric': {}
                ,
                'values': [
                    [1675218651.941, '0.032904559'],
                    [1675218666.941, '0.032904559']
                ]
            }
        ]
        """
        expression_query = ExpressionQuery().build_duration_seconds_query(url=url) + '[5m]'
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def success(self, provider: MonitorProvider, url: str):
        """
        http or tcp
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        '0.032904559'
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_success_query(url=url)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def success_period(self, provider: MonitorProvider, url: str):
        """
        http or tcp
        [
            {
                'metric': {}
                ,
                'values': [
                    [1675218651.941, '0.032904559'],
                    [1675218666.941, '0.032904559']
                ]
            }
        ]
        """
        expression_query = ExpressionQuery().build_success_query(url=url) + '[5m]'
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def http_duration_seconds(self, provider: MonitorProvider, url: str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        '0.032904559'
                    ]
                },
                ...
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_http_duration_seconds_query(url=url)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def http_duration_seconds_period(self, provider: MonitorProvider, url: str):
        """
        [
            {
                'metric': {
                },
                'values': [
                    [1675218651.941, '0.032904559'],
                    [1675218666.941, '0.032904559']
                ]
            },
            ...
        ]
        """
        expression_query = ExpressionQuery().build_http_duration_seconds_query(url=url) + '[5m]'
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def http_status_code_range(self, provider: MonitorProvider, url: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "values": [
                        [1630267851.781, "200"]
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_http_status_code_query(url=url)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query,
                                              start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def duration_seconds_range(self, provider: MonitorProvider, url: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "values": [
                        [1630267851.781, '0.032904559']
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_duration_seconds_query(url=url)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query,
                                              start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def success_range(self, provider: MonitorProvider, url: str, start: int, end: int, step: int):
        """
        http or tcp
        [
            {
                'metric': {}
                ,
                'values': [
                    [1675218651.941, '0.032904559'],
                    [1675218666.941, '0.032904559']
                ]
            }
        ]
        """
        expression_query = ExpressionQuery().build_success_query(url=url)
        api_url = self._build_query_range_api(
            endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def http_duration_seconds_range(self, provider: MonitorProvider, url: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        '0.032904559'
                    ]
                },
                ...
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_http_duration_seconds_query(url=url)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query,
                                              start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def _request_query_api(self, url: str):
        """
        :raises: Error
        """
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='monitor backend, web query api request timeout')
        except requests.exceptions.RequestException as exc:
            raise errors.Error(message=f'monitor backend, web query api request error, {str(exc)}')

        data = r.json()
        if 300 > r.status_code >= 200:
            s = data.get('status')
            if s == 'success':
                return data['data']['result']

        raise self._build_error(r)

    @staticmethod
    def _build_error(r):
        data = r.json()
        msg = f"status: {r.status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        return errors.Error(message=msg)

    def _build_query_api(self, endpoint_url: str, expression_query: str):
        return self.build_query_url(endpoint_url=endpoint_url, params={'query': expression_query})

    @staticmethod
    def _build_query_range_api(endpoint_url: str, expression_query: str, start, end, step):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={
            'query': expression_query, 'start': start, 'end': end, 'step': step,
            'partial_response': 'true', 'max_source_resolution': 0
        })
        url = f'{endpoint_url}/api/v1/query_range?{query}'
        return url

    @staticmethod
    def build_query_url(endpoint_url: str, params: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=params)
        url = f'{endpoint_url}/api/v1/query?{query}'
        return url

    def raw_query(self, provider: MonitorProvider, params: dict):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        '0.032904559'
                    ]
                },
                ...
            ]
        :raises: Error
        """
        api_url = self.build_query_url(endpoint_url=provider.endpoint_url, params=params)
        return self._request_query_api(api_url)


# if __name__ == "__main__":
#     # 将项目路径添加到系统搜寻路径当中，查找方式为从当前脚本开始，找到要调用的django项目的路径
#     import os, sys
#     from django import setup
#
#     sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gosc.settings')
#     setup()
#
#     mwq = MonitorWebsiteQueryAPI()
#     pd = MonitorProvider(endpoint_url="http://thanoswrite.cstcloud.cn:19192/")
#     r = mwq.http_status_code(provider=pd, url='http://www.nairc.com/')
#     print(r)
#     # r = mwq.http_status_code_period(provider=provider, url='http://www.nairc.com/')
#     # print(r)
#     r = mwq.duration_seconds(provider=pd, url='http://www.nairc.com/')
#     print(r)
#     # r = mwq.duration_seconds_period(provider=provider, url='http://www.nairc.com/')
#     # print(r)
