import time
from urllib import parse
from string import Template

import requests
import aiohttp

from core import errors
from monitor.utils import ThanosProvider


class ExpressionQuery:
    pd_nodes = 'up{job="$job", group_type="pd"}'
    tidb_nodes = 'up{job="$job", group_type="tidb"}'
    tikv_nodes = 'up{job="$job", group_type="tikv"}'

    connections_count = 'tidb_server_connections{job="$job"}'
    qps_count = 'sum(rate(tidb_executor_statement_total{job="$job"}[1m])) by (type)'
    region_count = 'sum(pd_cluster_status{job="$job", type="region_count"})'
    region_health = 'sum(pd_regions_status{job="$job"}) by (instance, type)'

    storage_capacity = 'pd_cluster_status{job="$job", type="storage_capacity"}'
    current_storage_size = 'pd_cluster_status{job="$job", type="storage_size"}'
    storage = 'pd_cluster_status{job="$job", type="storage_capacity"} or ' \
              'pd_cluster_status{job="$job", type="storage_size"}'
    server_cpu_usage = '100 - avg by (instance) (irate(node_cpu_seconds_total{job="$job", mode="idle"}[1m]) ) * 100'
    server_mem_usage = '100 - avg by (instance) (node_memory_MemAvailable_bytes{job="$job"} / ' \
                       'node_memory_MemTotal_bytes{job="$job"}) * 100'
    # server_disk_usage = '100 - avg by (instance) (node_filesystem_avail_bytes{job="$job", mountpoint="/data1"} / ' \
    #                     'node_filesystem_size_bytes{job="$job", mountpoint="/data1"}) * 100'

    server_disk_usage = '100 - avg by (instance) (node_filesystem_avail_bytes{job="$job", mountpoint="/data1"} / ' \
                        'node_filesystem_size_bytes{job="$job", mountpoint="/data1"} or ' \
                        'node_filesystem_avail_bytes{job="$job", mountpoint="/00_data"} / ' \
                        'node_filesystem_size_bytes{job="$job", mountpoint="/00_data"}) * 100'

    tmpl_pd_nodes = 'up{job="$job", group_type="pd"}'
    tmpl_tidb_nodes = 'up{job="$job", group_type="tidb"}'
    tmpl_tikv_nodes = 'up{job="$job", group_type="tikv"}'

    tmpl_connections_count = 'tidb_server_connections{job="$job"}'
    tmpl_qps_count = 'sum(rate(tidb_executor_statement_total{job="$job"}[1m])) by (type)'
    tmpl_region_status = 'sum(pd_regions_status{job="$job"}) by (instance, type)'
    tmpl_storage = 'pd_cluster_status{job="$job", type="storage_capacity"} or ' \
                   'pd_cluster_status{job="$job", type="storage_size"}'

    tmpl_cpu_count = 'count(node_cpu_seconds_total{job="$job", mode="system"}) by (instance)'
    tmpl_cpu_usage = '(1 - avg(rate(node_cpu_seconds_total{job="$job", mode="idle"}[1m])) by (instance)) * 100'
    tmpl_mem = 'node_memory_MemTotal_bytes{job="$job"} / 1073741824'  # GiB
    tmpl_mem_availabele = 'node_memory_MemAvailable_bytes{job="$job"} / 1073741824'  # GiB
    tmpl_root_dir_size = 'node_filesystem_size_bytes{job="$job", mountpoint="/"} / 1073741824'  # GiB
    tmpl_root_dir_avail_size = 'node_filesystem_avail_bytes{job="$job", mountpoint="/"} / 1073741824'  # GiB
    # TiB
    tmpl_node_size = 'node_filesystem_size_bytes{job="$job", mountpoint!="/", fstype=~"ext.*|xfs"} / 1073741824'
    tmpl_node_avail_size = 'node_filesystem_avail_bytes{job="$job", mountpoint!="/", fstype=~"ext.*|xfs"} / 1073741824'

    @staticmethod
    def expression(query_temp: str, job: str = None):
        expression_query = query_temp
        if job:
            expression_query = Template(query_temp).substitute(job=job)

        return expression_query

    def build_pd_nodes_query(self, job: str = None):
        return self.expression(query_temp=self.pd_nodes, job=job)

    def build_tidb_nodes_query(self, job: str = None):
        return self.expression(query_temp=self.tidb_nodes, job=job)

    def build_tikv_nodes_query(self, job: str = None):
        return self.expression(query_temp=self.tikv_nodes, job=job)

    def build_connections_count_query(self, job: str = None):
        return self.expression(query_temp=self.connections_count, job=job)

    def build_qps_count_query(self, job: str = None):
        return self.expression(query_temp=self.qps_count, job=job)

    def build_region_count_query(self, job: str = None):
        return self.expression(query_temp=self.region_count, job=job)

    def build_region_health_query(self, job: str = None):
        return self.expression(query_temp=self.region_health, job=job)

    def build_storage_capacity_query(self, job: str = None):
        return self.expression(query_temp=self.storage_capacity, job=job)

    def build_current_storage_size_query(self, job: str = None):
        return self.expression(query_temp=self.current_storage_size, job=job)

    def build_storage_query(self, job: str = None):
        return self.expression(query_temp=self.storage, job=job)

    def build_server_cpu_usage_query(self, job: str = None):
        return self.expression(query_temp=self.server_cpu_usage, job=job)

    def build_server_mem_usage_query(self, job: str = None):
        return self.expression(query_temp=self.server_mem_usage, job=job)

    def build_server_disk_usage_query(self, job: str = None):
        return self.expression(query_temp=self.server_disk_usage, job=job)


class MonitorTiDBQueryAPI:
    """
    response data example:
    {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {
                        "__name__": "node_memory_MemTotal_bytes",
                        "instance": "10.0.90.210:9100",
                        "job": "AIOPS-node",
                        "receive_cluster": "obs",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1631585555,
                        "67522076672"
                    ]
                }
            ]
        }
    }
    """
    _query_builder = ExpressionQuery()
    query_builder = _query_builder

    def pd_nodes(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_pd_nodes_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def tidb_nodes(self, provider: ThanosProvider, job: str):
        """
        :return:
            [
                {
                    "metric": {},
                    "value": [
                        1631585555,
                        "13"
                    ]
                }
            ]
        """
        expression_query = self._query_builder.build_tidb_nodes_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def tikv_nodes(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_tikv_nodes_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def connections_count(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_connections_count_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def qps_count(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_qps_count_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def region_count(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_region_count_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def region_health(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_region_health_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def storage_capacity(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_storage_capacity_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def current_storage_size(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_current_storage_size_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def storage(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_storage_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def server_cpu_usage(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_server_cpu_usage_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def server_mem_usage(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_server_mem_usage_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    def server_disk_usage(self, provider: ThanosProvider, job: str):
        """
        :return:
        """
        expression_query = self._query_builder.build_server_disk_usage_query(job=job)
        api_url = self._build_query_api(endpoint_url=provider.endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

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
        query = parse.urlencode(query={'query': expression_query, 'time': int(time.time())})
        url = f'{endpoint_url}/api/v1/query?{query}'
        return url

    def query_tag(self, endpoint_url: str, tag_tmpl: str, job: str):
        """
        :return:
        """
        expression_query = self.query_builder.expression(query_temp=tag_tmpl, job=job)
        api_url = self._build_query_api(endpoint_url=endpoint_url, expression_query=expression_query)
        return self._request_query_api(url=api_url)

    async def async_query_tag(self, endpoint_url: str, tag_tmpl: str, job: str):
        """
        :return:
        """
        expression_query = self.query_builder.expression(query_temp=tag_tmpl, job=job)
        api_url = self._build_query_api(endpoint_url=endpoint_url, expression_query=expression_query)
        return await self.async_request_query_api(url=api_url)

    @staticmethod
    async def async_request_query_api(url: str):
        """
        :raises: Error
        """
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(url=url, timeout=aiohttp.ClientTimeout(connect=5, total=30))
        except requests.exceptions.Timeout:
            raise errors.Error(message='tidb backend,query api request timeout')
        except requests.exceptions.RequestException:
            raise errors.Error(message='tidb backend,query api request error')

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
