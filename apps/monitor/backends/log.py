from urllib import parse

import requests
import aiohttp

from core import errors
from apps.monitor.utils import LokiProvider


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
    def query(self, provider: LokiProvider, querys: dict):
        """
        :return:
        """
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, querys=querys)
        return self._request_query_api(url=api_url)

    def query_log(self, provider: LokiProvider, querys: dict):
        """
        :return:
        """
        api_url = self._build_query_range_api(endpoint_url=provider.endpoint_url, querys=querys)
        return self._request_query_api(url=api_url)

    def _request_query_api(self, url: str):
        """
        :raises: Error
        """
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='log backend,query api request timeout')
        except requests.exceptions.RequestException:
            raise errors.Error(message='log backend,query api request error')

        if 300 > r.status_code >= 200:
            data = r.json()
            s = data.get('status')
            if s == 'success':
                return data['data']['result']

        raise self._build_error(r)

    @staticmethod
    def _build_error(r):
        try:
            data = r.json()
            msg = f"status: {r.status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        except Exception as e:
            msg = f"status: {r.status_code}, error: {r.text}"

        return errors.Error(message=msg)

    @staticmethod
    def _build_query_range_api(endpoint_url: str, querys: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=querys)
        return f'{endpoint_url}/loki/api/v1/query_range?{query}'

    @staticmethod
    def _build_query_api(endpoint_url: str, querys: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=querys)
        return f'{endpoint_url}/loki/api/v1/query?{query}'

    async def async_query(self, provider: LokiProvider, querys: dict, total_timeout: float = 30):
        """
        :return:
        """
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, querys=querys)
        return await self._async_request_query_api(url=api_url, total_timeout=total_timeout)

    @staticmethod
    async def _async_request_query_api(url: str, total_timeout: float = 30):
        """
        :raises: Error
        """
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(url=url, timeout=aiohttp.ClientTimeout(sock_connect=5, total=total_timeout))
                await r.read()
        except aiohttp.ClientConnectionError:
            raise errors.Error(message='log backend,query api request timeout')
        except aiohttp.ClientError as exc:
            raise errors.Error(message=f'log backend,query api request error: {str(exc)}')

        status_code = r.status
        if 300 > status_code >= 200:
            data = await r.json()
            s = data.get('status')
            if s == 'success':
                return data['data']['result']

        try:
            data = await r.json()
            msg = f"status: {status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        except Exception as e:
            text = await r.text()
            msg = f"status: {status_code}, error: {text}"

        raise errors.Error(message=msg)
