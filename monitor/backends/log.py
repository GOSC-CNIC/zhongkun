import requests
from urllib import parse

from core import errors
from monitor.models import MonitorProvider


class LogLokiAPI:
    """
    response data example:
    {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                    },
                    "values": [
                        [1631585555, "xxx"]
                    ]
                }
            ],
            "stats": {}
        }
    }
    """
    def query_log(self, provider: MonitorProvider, querys: dict):
        """
        :return:
        """
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, querys=querys)
        return self._request_query_api(url=api_url)

    def _request_query_api(self, url: str):
        """
        :raises: Error
        """
        # print(url)
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='log backend,query api request timeout')
        except requests.exceptions.RequestException:
            raise errors.Error(message='log backend,query api request error')

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

    @staticmethod
    def _build_query_range_api(endpoint_url: str, querys: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=querys)
        return f'{endpoint_url}/loki/api/v1/query_range?{query}'
