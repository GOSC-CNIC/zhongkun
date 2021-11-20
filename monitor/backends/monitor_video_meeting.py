import requests
from urllib import parse

from core import errors
from monitor.models import MonitorProvider


class ExpressionQuery:
    node_status = 'probe_success'
    node_lantency = 'probe_duration_seconds'

    @staticmethod
    def expression(tag: str):
        expression_query = tag

        return f'{expression_query}'

    def build_node_status_query(self):
        return self.expression(tag=self.node_status)

    def build_node_lantency_query(self):
        return self.expression(tag=self.node_lantency)


class MonitorVideoMeetingQueryAPI:
    def video_node_status(self, provider: MonitorProvider):
        expression_query = ExpressionQuery().build_node_status_query()
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    def video_node_lantency(self, provider: MonitorProvider):
        expression_query = ExpressionQuery().build_node_lantency_query()
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(api_url)

    @staticmethod
    def _build_query_api(endpoint_url: str, expression_query: str):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'query': expression_query})
        return f'{endpoint_url}/api/v1/query?{query}'

    def _request_query_api(self, url: str):
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='monitor backend, video meeting api request timeout')
        except requests.exceptions.RequestException:
            raise errors.Error(message='monitor backend, video meeting api request error')

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
