import asyncio

from django.utils.translation import gettext_lazy, gettext as _
from django.db import models

from core import errors
from monitor.backends.monitor_tidb import MonitorTiDBQueryAPI
from monitor.models import MonitorJobTiDB
from monitor.utils import build_thanos_provider, ThanosProvider
from monitor.serializers import MonitorJobTiDBSimpleSerializer


class TiDBQueryChoices(models.TextChoices):
    PD_NODES = 'pd_nodes', gettext_lazy('pd节点')
    TIDB_NODES = 'tidb_nodes', gettext_lazy('tidb节点')
    TIKV_NODES = 'tikv_nodes', gettext_lazy('tivk节点')
    CONNECTIONS_COUNT = 'connections_count', gettext_lazy('连接数')
    QPS = 'qps', gettext_lazy('每秒请求数')
    REGION_COUNT = 'region_count', gettext_lazy('副本数量')
    REGION_HEALTH = 'region_health', gettext_lazy('副本状态')
    STORAGE_CAPACITY = 'storage_capacity', gettext_lazy('存储总容量')
    CURRENT_STORAGE_SIZE = 'current_storage_size', gettext_lazy('当前存储容量')
    STORAGE = 'storage', gettext_lazy('存储总容量和当前已用容量')
    SERVER_CPU_USAGE = 'server_cpu_usage', gettext_lazy('主机CPU使用率')
    SERVER_MEM_USAGE = 'server_mem_usage', gettext_lazy('主机内存使用率')
    SERVER_DISK_USAGE = 'server_disk_usage', gettext_lazy('主机硬盘使用率')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class TiDBQueryV2Choices(models.TextChoices):
    PD_NODES = 'pd_nodes', gettext_lazy('pd节点')
    TIDB_NODES = 'tidb_nodes', gettext_lazy('tidb节点')
    TIKV_NODES = 'tikv_nodes', gettext_lazy('tivk节点')
    CONNECTIONS_COUNT = 'connections_count', gettext_lazy('连接数')
    QPS = 'qps', gettext_lazy('每秒请求数')
    REGION_STATUS = 'region_status', gettext_lazy('副本状态')
    STORAGE = 'storage', gettext_lazy('存储总容量和当前已用容量')
    SERVER_CPU_COUNT = 'server_cpu_count', gettext_lazy('主机CPU数量')
    SERVER_CPU_USAGE = 'server_cpu_usage', gettext_lazy('主机CPU使用率')
    SERVER_MEM_SIZE = 'server_mem_size', gettext_lazy('主机内存大小 GiB')
    SERVER_MEM_AVAIL = 'server_mem_avail', gettext_lazy('主机可用内存大小 GiB')
    SERVER_ROOT_DIR_SIZE = 'server_root_dir', gettext_lazy('主机根目录容量 GiB')
    SERVER_ROOT_DIR_AVAIL = 'server_root_dir_avail', gettext_lazy('主机根目录可用容量 GiB')
    SERVER_SIZE = 'server_size', gettext_lazy('主机存储容量 TiB')
    SERVER_AVAIL_SIZE = 'server_avail_size', gettext_lazy('主机可用存储容量 TiB')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class MonitorJobTiDBManager:
    backend = MonitorTiDBQueryAPI()

    tags_map = {
        TiDBQueryV2Choices.PD_NODES.value: backend.query_builder.tmpl_pd_nodes,
        TiDBQueryV2Choices.TIDB_NODES.value: backend.query_builder.tmpl_tidb_nodes,
        TiDBQueryV2Choices.TIKV_NODES.value: backend.query_builder.tmpl_tikv_nodes,
        TiDBQueryV2Choices.CONNECTIONS_COUNT.value: backend.query_builder.tmpl_connections_count,
        TiDBQueryV2Choices.QPS.value: backend.query_builder.tmpl_qps_count,
        TiDBQueryV2Choices.REGION_STATUS.value: backend.query_builder.tmpl_region_status,
        TiDBQueryV2Choices.STORAGE.value: backend.query_builder.tmpl_storage,
        TiDBQueryV2Choices.SERVER_CPU_COUNT.value: backend.query_builder.tmpl_cpu_count,
        TiDBQueryV2Choices.SERVER_CPU_USAGE.value: backend.query_builder.tmpl_cpu_usage,
        TiDBQueryV2Choices.SERVER_MEM_SIZE.value: backend.query_builder.tmpl_mem,
        TiDBQueryV2Choices.SERVER_MEM_AVAIL.value: backend.query_builder.tmpl_mem_availabele,
        TiDBQueryV2Choices.SERVER_ROOT_DIR_SIZE.value: backend.query_builder.tmpl_root_dir_size,
        TiDBQueryV2Choices.SERVER_ROOT_DIR_AVAIL.value: backend.query_builder.tmpl_root_dir_avail_size,
        TiDBQueryV2Choices.SERVER_SIZE.value: backend.query_builder.tmpl_node_size,
        TiDBQueryV2Choices.SERVER_AVAIL_SIZE.value: backend.query_builder.tmpl_node_avail_size,
    }

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobTiDB.objects.select_related('org_data_center').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, monitor_unit: MonitorJobTiDB):
        if tag == TiDBQueryChoices.ALL_TOGETHER.value:
            return self.query_together(monitor_unit=monitor_unit)

        return self._query(tag=tag, monitor_unit=monitor_unit)

    def query_together(self, monitor_unit: MonitorJobTiDB):
        ret = {}
        tags = TiDBQueryChoices.values
        tags.remove(TiDBQueryChoices.ALL_TOGETHER.value)
        for tag in tags:
            try:
                data = self._query(tag=tag, monitor_unit=monitor_unit)
            except errors.Error as exc:
                data = []

            ret[tag] = data

        return ret

    def _query(self, tag: str, monitor_unit: MonitorJobTiDB):
        """
        :return:
            [
                {
                    "monitor":{
                        "name": "",
                        "name_en": "",
                        "job_tag": "",
                        "id": "",
                        "creation": "2020-11-02T07:47:39.776384Z"
                    },
                    "metric": {                 # 此项的数据内容随查询数据类型变化
                        "__name__": "ceph_cluster_total_used_bytes",
                        "instance": "10.0.200.100:9283",
                        "job": "Fed-ceph",
                        "receive_cluster": "obs",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1630267851.781,
                        "0"
                    ]
                }
            ]
        :raises: Error
        """
        ret_data = []
        job_dict = MonitorJobTiDBSimpleSerializer(monitor_unit).data
        provider = build_thanos_provider(monitor_unit.org_data_center)
        r = self.request_data(provider=provider, tag=tag, job=monitor_unit.job_tag)
        for data in r:
            data['monitor'] = job_dict
            ret_data.append(data)

        return ret_data

    def request_data(self, provider: ThanosProvider, tag: str, job: str):
        """
        :return:
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
                        "0"                 # "0": 正常；”1“:警告
                    ]
                }
            ]
        :raises: Error
        """
        params = {'provider': provider, 'job': job}
        f = {
            TiDBQueryChoices.PD_NODES.value: self.backend.pd_nodes,
            TiDBQueryChoices.TIDB_NODES.value: self.backend.tidb_nodes,
            TiDBQueryChoices.TIKV_NODES.value: self.backend.tikv_nodes,
            TiDBQueryChoices.CONNECTIONS_COUNT.value: self.backend.connections_count,
            TiDBQueryChoices.REGION_COUNT.value: self.backend.region_count,
            TiDBQueryChoices.REGION_HEALTH.value: self.backend.region_health,
            TiDBQueryChoices.STORAGE_CAPACITY.value: self.backend.storage_capacity,
            TiDBQueryChoices.CURRENT_STORAGE_SIZE.value: self.backend.current_storage_size,
            TiDBQueryChoices.SERVER_CPU_USAGE.value: self.backend.server_cpu_usage,
            TiDBQueryChoices.SERVER_MEM_USAGE.value: self.backend.server_mem_usage,
            TiDBQueryChoices.SERVER_DISK_USAGE.value: self.backend.server_disk_usage,
            TiDBQueryChoices.QPS.value: self.backend.qps_count,
            TiDBQueryChoices.STORAGE.value: self.backend.storage,
        }[tag]

        return f(**params)

    def query_v2(self, tag: str, monitor_unit: MonitorJobTiDB):
        """
        {
            "monitor":{
                "name": "",
                "name_en": "",
                "job_tag": "",
                "id": "",
                "creation": "2020-11-02T07:47:39.776384Z"
            },
            "tag": [
                {
                    "metric": {                 # 此项的数据内容随查询数据类型变化
                        "__name__": "ceph_cluster_total_used_bytes",
                        "instance": "10.0.200.100:9283",
                        "job": "Fed-ceph",
                        "receive_cluster": "obs",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1630267851.781,
                        "0"
                    ]
                }
            ]
        }
        """
        job_dict = MonitorJobTiDBSimpleSerializer(monitor_unit).data
        if tag == TiDBQueryV2Choices.ALL_TOGETHER.value:
            data = self.async_query_together_v2(monitor_unit=monitor_unit)
        else:
            data = self._query_v2(tag=tag, monitor_unit=monitor_unit)

        data['monitor'] = job_dict
        return data

    def _query_v2(self, tag: str, monitor_unit: MonitorJobTiDB):
        """
        :return:
            { tag: []}
        :raises: Error
        """
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tag_tmpl = self.tags_map[tag]
        r = self.backend.query_tag(endpoint_url=provider.endpoint_url, tag_tmpl=tag_tmpl, job=monitor_unit.job_tag)
        return {tag: r}

    def async_query_together_v2(self, monitor_unit: MonitorJobTiDB):
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tags = TiDBQueryV2Choices.values
        tags.remove(TiDBQueryV2Choices.ALL_TOGETHER.value)

        tasks = [self.req_tag(unit=monitor_unit, endpoint_url=provider.endpoint_url, tag=tag) for tag in tags]
        results = asyncio.run(self.do_async_requests(tasks))
        data = {}
        errs = {}
        for r in results:
            tag, tag_data = r
            if isinstance(tag_data, Exception):
                data[tag] = []
                errs[tag] = str(tag_data)
            else:
                data[tag] = tag_data

        if errs:
            data['errors'] = errs

        return data

    @staticmethod
    async def do_async_requests(tasks):
        return await asyncio.gather(*tasks, return_exceptions=True)

    async def req_tag(self, unit: MonitorJobTiDB, endpoint_url: str, tag: str):
        try:
            tag_tmpl = self.tags_map[tag]
            ret = await self.backend.async_query_tag(
                endpoint_url=endpoint_url, tag_tmpl=tag_tmpl, job=unit.job_tag)
        except Exception as exc:
            err = Exception(f'{unit.name}, {endpoint_url}, {tag},{exc}')
            return tag, err

        return tag, ret
