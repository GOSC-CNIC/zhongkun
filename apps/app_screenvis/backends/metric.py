from urllib import parse
from string import Template

import requests
import aiohttp

from apps.app_screenvis.utils import errors


class BaseExpressionQuery:
    @staticmethod
    def render_expression(tmpl: str, job: str = None):
        expression_query = tmpl
        if job:
            expression_query = Template(tmpl).substitute(job=job)

        return expression_query


class CephExpressionQuery(BaseExpressionQuery):
    # tmpl_health_status = 'ceph_health_status{job="$job"}'
    # tmpl_health_detail = 'ceph_health_detail{job="$job"} == 1'
    tmpl_health_status_detail = 'ceph_health_status{job="$job"} or ceph_health_detail{job="$job"} == 1'
    tmpl_total_bytes = 'ceph_cluster_total_bytes{job="$job"} / 1099511627776'    # 单位TiB
    tmpl_total_used_bytes = 'ceph_cluster_total_used_bytes{job="$job"} / 1099511627776'  # 单位TiB
    # tmpl_osd_in = 'ceph_osd_in{job="$job"} == 1'
    tmpl_osd_in_count = 'count(ceph_osd_in{job="$job"} == 1)'
    # tmpl_osd_out = 'ceph_osd_in{job="$job"} == 0'
    tmpl_osd_out_count = 'count(ceph_osd_in{job="$job"} == 0) or vector(0)'
    # tmpl_osd_up = 'ceph_osd_up{job="$job"} == 1'
    tmpl_osd_up_count = 'count(ceph_osd_up{job="$job"} == 1)'
    # tmpl_osd_down = 'ceph_osd_up{job="$job"} == 0'
    tmpl_osd_down_count = 'count(ceph_osd_up{job="$job"} == 0) or vector(0)'
    tmpl_mon_status = 'ceph_mon_quorum_status{job="$job"}'
    tmpl_mgr_status = 'ceph_mgr_status{job="$job"}'
    # tmpl_pool_meta = 'ceph_pool_metadata{job="$job"}'
    tmpl_pool_count = 'count(ceph_pool_metadata{job="$job"})'
    tmpl_pg_active_count = 'sum(ceph_pg_active{job="$job"})'
    tmpl_pg_unactive_count = 'sum(ceph_pg_total{job="$job"} - ceph_pg_active{job="$job"})'
    tmpl_pg_degraded_count = 'sum(ceph_pg_degraded{job="$job"})'
    tmpl_obj_degraded = 'ceph_num_objects_degraded{job="$job"}'
    tmpl_obj_misplaced = 'ceph_num_objects_misplaced{job="$job"}'


class HostExpressionQuery(BaseExpressionQuery):
    tmpl_up_count = 'count(up{job="$job"} == 1) or vector(0)'
    tmpl_down = 'up{job="$job"} == 0'
    tmpl_host_count = 'count(node_uname_info{job="$job"})'

    tmpl_cpu_count = 'count(node_cpu_seconds_total{job="$job", mode="system"})'
    tmpl_cpu_usage = '(1 - avg(rate(node_cpu_seconds_total{job="$job", mode="idle"}[1m]))) * 100'
    tmpl_node_cpu_usage = '(1 - avg(rate(node_cpu_seconds_total{job="$job", mode="idle"}[1m])) by (instance)) * 100'
    tmpl_mem_size = 'sum(node_memory_MemTotal_bytes{job="$job"}) / 1073741824'  # GiB
    tmpl_mem_availabele = 'sum(node_memory_MemAvailable_bytes{job="$job"}) / 1073741824'   # GiB
    tmpl_node_mem_avail_size = 'node_memory_MemAvailable_bytes{job="$job"} / 1073741824'  # GiB
    tmpl_node_root_avail_size = 'node_filesystem_avail_bytes{job="$job", mountpoint="/"} / 1073741824'  # GiB
    tmpl_node_mem_hugepage_usage = '(1 - node_memory_HugePages_Free{job="$job"} / ' \
                                   'node_memory_HugePages_Total{job="$job"}) * 100'
    tmpl_node_mem_hugepage_total = 'node_memory_HugePages_Total{job="$job"}'
    tmpl_node_mem_hugepage_free = 'node_memory_HugePages_Free{job="$job"}'
    # MiB/s
    # tmpl_net_rate_in = 'rate(node_network_receive_bytes_total{job="$job", device!~"lo|br_.*|vnet.*"}[1m]) * on(' \
    #                    'job, instance, device) (node_network_info{operstate="up"} == 1) / 8388608'
    # tmpl_net_rate_out = 'rate(node_network_transmit_bytes_total{job="$job", device!~"lo|br_.*|vnet.*"}[1m]) * on(' \
    #                     'job, instance, device) (node_network_info{operstate="up"} == 1) / 8388608'
    tmpl_net_rate_in = 'sum(rate(node_network_receive_bytes_total{job="$job", device!="lo"}[2m])) / 125000'     # Mib/s
    tmpl_net_rate_out = 'sum(rate(node_network_transmit_bytes_total{job="$job", device!="lo"}[2m])) / 125000'   # Mib/s


class TiDBExpressionQuery(BaseExpressionQuery):
    tmpl_pd_nodes = 'up{job="$job", group_type="pd"}'
    tmpl_tidb_nodes = 'up{job="$job", group_type="tidb"}'
    tmpl_tikv_nodes = 'up{job="$job", group_type="tikv"}'

    tmpl_connections_count = 'sum(tidb_server_connections{job="$job"})'
    tmpl_qps_count = 'sum(rate(tidb_executor_statement_total{job="$job"}[1m]))'
    # tmpl_region_status = 'sum(pd_regions_status{job="$job"}) by (instance, type)'
    tmpl_region_count = 'sum(pd_regions_status{job="$job"})'
    tmpl_storage = 'pd_cluster_status{job="$job", type="storage_capacity"} or ' \
                   'pd_cluster_status{job="$job", type="storage_size"}'

    tmpl_cpu_count = 'count(node_cpu_seconds_total{job="$job", mode="system"})'
    tmpl_cpu_usage = '(1 - avg(rate(node_cpu_seconds_total{job="$job", mode="idle"}[1m]))) * 100'
    tmpl_mem = 'sum(node_memory_MemTotal_bytes{job="$job"}) / 1073741824'  # GiB
    tmpl_mem_availabele = 'sum(node_memory_MemAvailable_bytes{job="$job"}) / 1073741824'  # GiB
    # tmpl_root_dir_size = 'node_filesystem_size_bytes{job="$job", mountpoint="/"} / 1073741824'  # GiB
    # tmpl_root_dir_avail_size = 'node_filesystem_avail_bytes{job="$job", mountpoint="/"} / 1073741824'  # GiB
    # TiB
    tmpl_node_size = 'node_filesystem_size_bytes{job="$job", mountpoint!="/", fstype=~"ext.*|xfs"} / 1073741824'
    tmpl_node_avail_size = 'node_filesystem_avail_bytes{job="$job", mountpoint!="/", fstype=~"ext.*|xfs"} / 1073741824'


class MetricQueryAPI:
    ceph_query_builder = CephExpressionQuery
    host_query_builder = HostExpressionQuery
    tidb_query_builder = TiDBExpressionQuery

    def request_query_api(self, url: str):
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

        raise self._build_error(r)

    @staticmethod
    def _build_error(r):
        data = r.json()
        msg = f"status: {r.status_code}, errorType: {data.get('errorType')}, error: {data.get('error')}"
        return errors.Error(message=msg)

    @staticmethod
    def _build_query_range_api(endpoint_url: str, expression_query: str, start, end, step):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query={'query': expression_query, 'start': start, 'end': end, 'step': step})
        url = f'{endpoint_url}/api/v1/query_range?{query}'
        return url

    @staticmethod
    def _build_query_url(endpoint_url: str, querys: dict):
        endpoint_url = endpoint_url.rstrip('/')
        query = parse.urlencode(query=querys)
        return f'{endpoint_url}/api/v1/query?{query}'

    async def async_raw_query(self, endpoint_url: str, querys: dict):
        api_url = self._build_query_url(endpoint_url=endpoint_url, querys=querys)
        return await self.async_request_query_api(url=api_url)

    def query_range_tag(
            self, endpoint_url: str, tag_tmpl: str, job: str, start: int, end: int, step: int,
            query_render: BaseExpressionQuery = None
    ):
        if not query_render:
            query_render = BaseExpressionQuery

        expression_query = query_render.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_range_api(
            endpoint_url=endpoint_url, expression_query=expression_query, start=start, end=end, step=step)
        return self.request_query_api(api_url)

    def query_tag(self, endpoint_url: str, tag_tmpl: str, job: str, query_render: BaseExpressionQuery = None):
        if not query_render:
            query_render = BaseExpressionQuery

        expression_query = query_render.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_url(endpoint_url=endpoint_url, querys={'query': expression_query})
        return self.request_query_api(url=api_url)

    async def async_query_tag(
            self, endpoint_url: str, tag_tmpl: str, job: str, query_render: BaseExpressionQuery = None
    ):
        if not query_render:
            query_render = BaseExpressionQuery

        expression_query = query_render.render_expression(tmpl=tag_tmpl, job=job)
        api_url = self._build_query_url(endpoint_url=endpoint_url, querys={'query': expression_query})
        return await self.async_request_query_api(url=api_url)

    @staticmethod
    async def async_request_query_api(url: str):
        """
        :raises: Error
        """
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.get(url=url, timeout=aiohttp.ClientTimeout(connect=10, total=30))
        except aiohttp.ClientConnectionError:
            raise errors.Error(message='backend query api request timeout')
        except aiohttp.ClientError as exc:
            raise errors.Error(message=f'backend query api request error; {str(exc)}')

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
