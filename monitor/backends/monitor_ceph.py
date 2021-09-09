import requests
from urllib import parse

from core import errors
from monitor.models import MonitorProvider


class ExpressionQuery:
    ceph_health_status = 'ceph_health_status'
    ceph_cluster_total_bytes = 'ceph_cluster_total_bytes'
    ceph_cluster_total_used_bytes = 'ceph_cluster_total_used_bytes'
    ceph_osd_in = 'ceph_osd_in'
    ceph_osd_up = 'ceph_osd_up'

    @staticmethod
    def expression(tag: str, job: str = None):
        expression_query = tag
        if job:
            expression_query = f'{expression_query}{{job="{job}"}}'

        return expression_query

    def build_ceph_health_status_query(self, job: str = None):
        return self.expression(tag=self.ceph_health_status, job=job)

    def build_ceph_cluster_total_bytes_query(self, job: str = None):
        return self.expression(tag=self.ceph_cluster_total_bytes, job=job)

    def build_ceph_cluster_total_used_bytes_query(self, job: str = None):
        return self.expression(tag=self.ceph_cluster_total_used_bytes, job=job)

    def build_ceph_osd_in_query(self, job: str = None):
        """
        sum(ceph_osd_in{job="Fed-ceph"})
        """
        expression_query = self.expression(tag=self.ceph_osd_in, job=job)
        return f'sum({expression_query})'

    def build_ceph_osd_up_query(self, job: str = None):
        """
        sum(ceph_osd_up{job="Fed-ceph"})
        """
        expression_query = self.expression(tag=self.ceph_osd_up, job=job)
        return f'sum({expression_query})'

    def build_ceph_osd_out_query(self, job: str = None):
        """
        count(ceph_osd_up{job="Fed-ceph"}) - count(ceph_osd_in{job="Fed-ceph"})
        """
        expression_up = self.expression(tag=self.ceph_osd_up, job=job)
        expression_in = self.expression(tag=self.ceph_osd_up, job=job)
        return f'count({expression_up}) - count({expression_in})'

    def build_ceph_osd_down_query(self, job: str = None):
        """
        count(ceph_osd_up{job="$job"} == 0) OR vector(0)
        """
        expression_up = self.expression(tag=self.ceph_osd_up, job=job)
        return f'count({expression_up} == 0)  OR vector(0)'


class MonitorCephQueryAPI:
    """
    response data example:
    [
        {
            "metric": {
                "__name__": "ceph_cluster_total_used_bytes",
                "instance": "10.0.200.100:9283",
                "job": "Fed-ceph",
                "receive_cluster": "obs",
                "receive_replica": "0",
                "tenant_id": "default-tenant"
            },
            "value": [
                1630267851.781,
                "1622079296241664"
            ]
        }
    ]
    """
    def ceph_health_status(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "0"                 # "0": 正常；”1“:警告
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_health_status_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_cluster_total_bytes(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "1622079296241664"                 # bytes
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_cluster_total_bytes_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_cluster_total_used_bytes(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "1622079296241664"                 # bytes
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_cluster_total_used_bytes_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_osd_in(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920515.483,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_in_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_osd_out(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920739.865,
                        "0"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_out_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_osd_up(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920939.236,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_up_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_osd_down(self, provider: MonitorProvider, job:str):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920939.236,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_down_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def ceph_health_status_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "0"                 # "0": 正常；”1“:警告
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_health_status_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_cluster_total_bytes_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "1622079296241664"                 # bytes
                    ]
                }
            ]
        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_cluster_total_bytes_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_cluster_total_used_bytes_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630267851.781,
                        "1622079296241664"                 # bytes
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_cluster_total_used_bytes_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_osd_in_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920515.483,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_in_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_osd_out_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920739.865,
                        "0"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_out_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_osd_up_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920939.236,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_up_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def ceph_osd_down_range(self, provider: MonitorProvider, job: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    ...
                    "value": [
                        1630920939.236,
                        "375"
                    ]
                }
            ]

        :raises: Error
        """
        expression_query = ExpressionQuery().build_ceph_osd_down_query(job=job)
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def _request_query_api(self, url: str):
        """
        :raises: Error
        """
        r = requests.get(url=url)
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
        errors.Error(message=msg)

    @staticmethod
    def _build_query_api(endpoint_url: str, expression_query: str):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'query': expression_query})
        url = f'{endpoint_url}/api/v1/query?{query}'
        return url

    @staticmethod
    def _build_query_range_api(endpoint_url: str, expression_query: str, start, end, step):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'query': expression_query, 'start': start, 'end': end, 'step': step})
        url = f'{endpoint_url}/api/v1/query_range?{query}'
        return url



