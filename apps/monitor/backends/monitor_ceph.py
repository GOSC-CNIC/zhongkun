from urllib import parse
from string import Template

import requests
import aiohttp

from core import errors


class ExpressionQuery:
    ceph_health_status = 'ceph_health_status{job="$job"}'
    ceph_cluster_total_bytes = 'ceph_cluster_total_bytes{job="$job"}'
    ceph_cluster_total_used_bytes = 'ceph_cluster_total_used_bytes{job="$job"}'
    ceph_osd_in = 'ceph_osd_in{job="$job"}'
    ceph_osd_up = 'ceph_osd_up{job="$job"}'
    ceph_osd_in_count = 'sum(ceph_osd_in{job="$job"})'
    ceph_osd_up_count = 'sum(ceph_osd_up{job="$job"})'
    ceph_osd_out_count = 'count(ceph_osd_up{job="$job"}) - count(ceph_osd_in{job="$job"})'
    ceph_osd_down_count = 'count(ceph_osd_up{job="$job"} == 0) or vector(0)'

    tmpl_health_status = 'ceph_health_status{job="$job"}'
    tmpl_health_detail = 'ceph_health_detail{job="$job"} == 1'
    tmpl_health_status_detail = 'ceph_health_status{job="$job"} or ceph_health_detail{job="$job"} == 1'
    tmpl_total_bytes = 'ceph_cluster_total_bytes{job="$job"} / 1099511627776'    # 单位TiB
    tmpl_total_used_bytes = 'ceph_cluster_total_used_bytes{job="$job"} / 1099511627776'  # 单位TiB
    tmpl_osd_in_count = 'count(ceph_osd_in{job="$job"} == 1)'
    tmpl_osd_in = 'ceph_osd_in{job="$job"} == 1'
    tmpl_osd_out = 'ceph_osd_in{job="$job"} == 0'
    tmpl_osd_up = 'ceph_osd_up{job="$job"} == 1'
    tmpl_osd_up_count = 'count(ceph_osd_up{job="$job"} == 1)'
    tmpl_osd_down = 'ceph_osd_up{job="$job"} == 0'
    tmpl_mon_status = 'ceph_mon_quorum_status{job="$job"}'
    tmpl_mgr_status = 'ceph_mgr_status{job="$job"}'
    tmpl_pool_meta = 'ceph_pool_metadata{job="$job"}'
    tmpl_pg_active = 'ceph_pg_active{job="$job"}'
    tmpl_pg_unactive = 'ceph_pg_total{job="$job"} - ceph_pg_active{job="$job"}'
    tmpl_pg_degraded = 'ceph_pg_degraded{job="$job"}'
    tmpl_obj_degraded = 'ceph_num_objects_degraded{job="$job"}'
    tmpl_obj_misplaced = 'ceph_num_objects_misplaced{job="$job"}'

    @staticmethod
    def render_expression(tmpl: str, job: str = None):
        expression_query = tmpl
        if job:
            expression_query = Template(tmpl).substitute(job=job)

        return expression_query


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
            "value": [1630267851.781, "1622079296241664"]       # when query
            "values": [                                         # when query_rang
                [1630267851.781, "1622079296241664"]
            ]
        }
    ]
    """
    query_builder = ExpressionQuery()

    def query_range_tag(self, endpoint_url: str, tag_tmpl: str, job: str, start: int, end: int, step: int):
        """
        :return:
        """
        expression_query = self.query_builder.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_range_api(
            endpoint_url=endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self._request_query_api(api_url)

    def _request_query_api(self, url: str):
        """
        :raises: Error
        """
        try:
            r = requests.get(url=url, timeout=(6, 30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='monitor backend, ceph query api request timeout')
        except requests.exceptions.RequestException:
            raise errors.Error(message='monitor backend, ceph query api request error')

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

    def query_tag(self, endpoint_url: str, tag_tmpl: str, job: str):
        """
        :return:
        """
        expression_query = self.query_builder.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_api(endpoint_url=endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    async def async_query_tag(self, endpoint_url: str, tag_tmpl: str, job: str):
        """
        :return:
        """
        expression_query = self.query_builder.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_api(endpoint_url=endpoint_url, expression_query=expression_query)
        return await self.async_request_query_api(url=api_url)

    @staticmethod
    async def async_request_query_api(url: str):
        """
        :raises: Error
        """
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(url=url, timeout=aiohttp.ClientTimeout(sock_connect=5, total=30))
                await r.read()
        except aiohttp.ClientConnectionError:
            raise errors.Error(message='ceph backend,query api request timeout')
        except aiohttp.ClientError as exc:
            raise errors.Error(message=f'ceph backend,query api request error: {str(exc)}')

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
