import asyncio

from django.db import models
from django.utils.translation import gettext_lazy, gettext as _

from apps.app_screenvis.utils import errors
from apps.app_screenvis.utils import build_metric_provider, MetricProvider
from apps.app_screenvis.serializers import MetricMntrUnitSimpleSerializer
from apps.app_screenvis.models import MetricMonitorUnit
from apps.app_screenvis.backends import MetricQueryAPI


ALL_TOGETHER_VALUE = 'all_together'


class HostQueryChoices(models.TextChoices):
    HOST_UP_COUNT = 'up_count', gettext_lazy('在线主机数')
    HOST_DOWN = 'down', gettext_lazy('掉线主机')
    # HOST_COUNT = 'host_count', gettext_lazy('主机总数')
    HOST_CPU_USAGE = 'cpu_usage', gettext_lazy('主机CPU使用率')
    HOST_MEM_AVAIL_SIZE = 'mem_avail_size', gettext_lazy('主机内存可用容量(GiB)')
    HOST_ROOT_AVAIL_SIZE = 'root_avail_size', gettext_lazy('主机根目录可用容量(GiB)')
    HOST_MEM_HUGEPAGE_USAGE = 'mem_hugepage_usage', gettext_lazy('主机大页内存使用率')
    ALL_TOGETHER = ALL_TOGETHER_VALUE, gettext_lazy('一起查询所有指标')


class CephQueryChoices(models.TextChoices):
    HEALTH_STATUS_DETAIL = 'health_status_detail', gettext_lazy('Ceph健康状态和异常信息')
    CLUSTER_SIZE = 'cluster_size', gettext_lazy('Ceph集群存储容量TiB')
    CLUSTER_USED_SIZE = 'cluster_used_size', gettext_lazy('Ceph集群已用存储容量TiB')
    OSD_IN_COUNT = 'osd_in_count', gettext_lazy('Ceph集群内OSD数')
    OSD_OUT_COUNT = 'osd_out_count', gettext_lazy('Ceph集群外OSD数')
    OSD_UP_COUNT = 'osd_up_count', gettext_lazy('Ceph集群活着且在运行OSD数')
    OSD_DOWN_COUNT = 'osd_down_count', gettext_lazy('Ceph集群挂了且不再运行OSD数')
    MON_STATUS = 'mon_status', gettext_lazy('mon状态')
    MGR_STATUS = 'mgr_status', gettext_lazy('mgr状态')
    POOL_COUNT = 'pool_count', gettext_lazy('Pool数量')
    PG_ACTIVE_COUNT = 'pg_active_count', gettext_lazy('活动的PG数')
    PG_UNACTIVE_COUNT = 'pg_unactive_count', gettext_lazy('非活动的PG数')
    PG_DEGRADED_COUNT = 'pg_degraded_count', gettext_lazy('degraded降级PG数')
    OBJ_DEGRADED = 'obj_degraded', gettext_lazy('degraded降级对象数量')
    OBJ_MISPLACED = 'obj_misplaced', gettext_lazy('misplaced存储错位对象数量')
    ALL_TOGETHER = ALL_TOGETHER_VALUE, gettext_lazy('一起查询所有指标')


class TiDBQueryChoices(models.TextChoices):
    PD_NODES = 'pd_nodes', gettext_lazy('pd节点')
    TIDB_NODES = 'tidb_nodes', gettext_lazy('tidb节点')
    TIKV_NODES = 'tikv_nodes', gettext_lazy('tivk节点')
    CONNECTIONS_COUNT = 'connections_count', gettext_lazy('连接数')
    QPS_COUNT = 'qps_count', gettext_lazy('每秒请求数')
    # REGION_STATUS = 'region_status', gettext_lazy('副本状态')
    # REGION_COUNT = 'region_count', gettext_lazy('副本异常状态数量')
    STORAGE = 'storage', gettext_lazy('存储总容量和当前已用容量')
    # SERVER_CPU_COUNT = 'server_cpu_count', gettext_lazy('主机CPU数量')
    SERVER_CPU_USAGE = 'server_cpu_usage', gettext_lazy('主机CPU使用率')
    SERVER_MEM_SIZE = 'server_mem_size', gettext_lazy('主机内存大小 GiB')
    SERVER_MEM_AVAIL = 'server_mem_avail', gettext_lazy('主机可用内存大小 GiB')
    # SERVER_SIZE = 'server_size', gettext_lazy('主机存储容量 TiB')
    # SERVER_AVAIL_SIZE = 'server_avail_size', gettext_lazy('主机可用存储容量 TiB')
    ALL_TOGETHER = ALL_TOGETHER_VALUE, gettext_lazy('一起查询所有指标')


class MetricQueryManager:
    backend = MetricQueryAPI()

    ceph_tag_tmpl_map = {
        CephQueryChoices.HEALTH_STATUS_DETAIL.value: backend.ceph_query_builder.tmpl_health_status_detail,
        CephQueryChoices.CLUSTER_SIZE.value: backend.ceph_query_builder.tmpl_total_bytes,
        CephQueryChoices.CLUSTER_USED_SIZE.value: backend.ceph_query_builder.tmpl_total_used_bytes,
        CephQueryChoices.OSD_IN_COUNT.value: backend.ceph_query_builder.tmpl_osd_in_count,
        CephQueryChoices.OSD_OUT_COUNT.value: backend.ceph_query_builder.tmpl_osd_out_count,
        CephQueryChoices.OSD_UP_COUNT.value: backend.ceph_query_builder.tmpl_osd_up_count,
        CephQueryChoices.OSD_DOWN_COUNT.value: backend.ceph_query_builder.tmpl_osd_down_count,
        CephQueryChoices.MON_STATUS.value: backend.ceph_query_builder.tmpl_mon_status,
        CephQueryChoices.MGR_STATUS.value: backend.ceph_query_builder.tmpl_mgr_status,
        CephQueryChoices.POOL_COUNT.value: backend.ceph_query_builder.tmpl_pool_count,
        CephQueryChoices.PG_ACTIVE_COUNT.value: backend.ceph_query_builder.tmpl_pg_active_count,
        CephQueryChoices.PG_UNACTIVE_COUNT.value: backend.ceph_query_builder.tmpl_pg_unactive_count,
        CephQueryChoices.PG_DEGRADED_COUNT.value: backend.ceph_query_builder.tmpl_pg_degraded_count,
        CephQueryChoices.OBJ_DEGRADED.value: backend.ceph_query_builder.tmpl_obj_degraded,
        CephQueryChoices.OBJ_MISPLACED.value: backend.ceph_query_builder.tmpl_obj_misplaced,
    }

    host_tag_tmpl_map = {
        HostQueryChoices.HOST_UP_COUNT.value: backend.host_query_builder.tmpl_up_count,
        HostQueryChoices.HOST_DOWN.value: backend.host_query_builder.tmpl_down,
        HostQueryChoices.HOST_CPU_USAGE.value: backend.host_query_builder.tmpl_node_cpu_usage,
        HostQueryChoices.HOST_MEM_AVAIL_SIZE.value: backend.host_query_builder.tmpl_node_mem_avail_size,
        HostQueryChoices.HOST_ROOT_AVAIL_SIZE.value: backend.host_query_builder.tmpl_node_root_avail_size,
        HostQueryChoices.HOST_MEM_HUGEPAGE_USAGE.value: backend.host_query_builder.tmpl_node_mem_hugepage_usage,
    }

    tidb_tag_tmpl_map = {
        TiDBQueryChoices.PD_NODES.value: backend.tidb_query_builder.tmpl_pd_nodes,
        TiDBQueryChoices.TIDB_NODES.value: backend.tidb_query_builder.tmpl_tidb_nodes,
        TiDBQueryChoices.TIKV_NODES.value: backend.tidb_query_builder.tmpl_tikv_nodes,
        TiDBQueryChoices.CONNECTIONS_COUNT.value: backend.tidb_query_builder.tmpl_connections_count,
        TiDBQueryChoices.QPS_COUNT.value: backend.tidb_query_builder.tmpl_qps_count,
        # TiDBQueryChoices.REGION_COUNT.value: backend.tidb_query_builder.tmpl_region_count,
        TiDBQueryChoices.STORAGE.value: backend.tidb_query_builder.tmpl_storage,
        # TiDBQueryChoices.SERVER_CPU_COUNT.value: backend.tidb_query_builder.tmpl_cpu_count,
        TiDBQueryChoices.SERVER_CPU_USAGE.value: backend.tidb_query_builder.tmpl_cpu_usage,
        TiDBQueryChoices.SERVER_MEM_SIZE.value: backend.tidb_query_builder.tmpl_mem,
        TiDBQueryChoices.SERVER_MEM_AVAIL.value: backend.tidb_query_builder.tmpl_mem_availabele
    }

    def get_choices_tag_tmpl_map(self, metric_unit: MetricMonitorUnit):
        if metric_unit.unit_type == MetricMonitorUnit.UnitType.HOST.value:
            return HostQueryChoices, self.host_tag_tmpl_map
        elif metric_unit.unit_type == MetricMonitorUnit.UnitType.CEPH.value:
            return CephQueryChoices, self.ceph_tag_tmpl_map
        elif metric_unit.unit_type == MetricMonitorUnit.UnitType.TIDB.value:
            return TiDBQueryChoices, self.tidb_tag_tmpl_map
        else:
            raise errors.BadRequest(message=_('无效的指标单元类型'))

    def query(self, tag: str, metric_unit: MetricMonitorUnit):
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
        query_choices, tags_map = self.get_choices_tag_tmpl_map(metric_unit)
        provider = build_metric_provider(metric_unit.data_center)
        job_dict = MetricMntrUnitSimpleSerializer(metric_unit).data
        if tag == ALL_TOGETHER_VALUE:
            tags = query_choices.values
            tags.remove(ALL_TOGETHER_VALUE)
            data = self.async_query_together(metric_unit=metric_unit, provider=provider, tags=tags, tag_map=tags_map)
        else:
            data = self._query(metric_unit=metric_unit, provider=provider, tag=tag, tag_map=tags_map)

        data['monitor'] = job_dict
        return data

    def _query(self, metric_unit: MetricMonitorUnit, provider: MetricProvider, tag: str, tag_map: dict):
        """
        :return:
            { tag: []}
        :raises: Error
        """
        tag_tmpl = tag_map[tag]
        r = self.backend.query_tag(endpoint_url=provider.endpoint_url, tag_tmpl=tag_tmpl, job=metric_unit.job_tag)
        return {tag: r}

    def async_query_together(
            self, metric_unit: MetricMonitorUnit, provider: MetricProvider, tags: list, tag_map: dict
    ):
        tasks = [
            self.req_tag(
                backend=self.backend, unit=metric_unit, endpoint_url=provider.endpoint_url,
                tag=tag, tag_tmpl=tag_map[tag]
            ) for tag in tags
        ]
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

    @staticmethod
    async def req_tag(backend, unit: MetricMonitorUnit, endpoint_url: str, tag: str, tag_tmpl: str):
        try:
            ret = await backend.async_query_tag(
                endpoint_url=endpoint_url, tag_tmpl=tag_tmpl, job=unit.job_tag)
        except Exception as exc:
            err = Exception(f'{unit.name}, {endpoint_url}, {tag},{exc}')
            return tag, err

        return tag, ret
