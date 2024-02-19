import asyncio

from django.db import models
from django.utils.translation import gettext_lazy, gettext as _

from core import errors
from monitor.utils import build_thanos_provider, ThanosProvider
from monitor.serializers import MonitorJobCephSerializer
from monitor.models import MonitorJobCeph
from monitor.backends.monitor_ceph import MonitorCephQueryAPI


class CephQueryChoices(models.TextChoices):
    HEALTH_STATUS = 'health_status', gettext_lazy('Ceph健康状态')
    CLUSTER_TOTAL_BYTES = 'cluster_total_bytes', gettext_lazy('Ceph集群存储容量')
    CLUSTER_TOTAL_USED_BYTES = 'cluster_total_used_bytes', gettext_lazy('Ceph集群已用存储容量')
    OSD_IN = 'osd_in', gettext_lazy('Ceph集群内OSD数')
    OSD_OUT = 'osd_out', gettext_lazy('Ceph集群外OSD数')
    OSD_UP = 'osd_up', gettext_lazy('Ceph集群活着且在运行OSD数')
    OSD_DOWN = 'osd_down', gettext_lazy('Ceph集群挂了且不再运行OSD数')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class CephQueryV2Choices(models.TextChoices):
    HEALTH_STATUS_DETAIL = 'health_status_detail', gettext_lazy('Ceph健康状态和异常信息')
    CLUSTER_SIZE = 'cluster_size', gettext_lazy('Ceph集群存储容量TiB')
    CLUSTER_USED_SIZE = 'cluster_used_size', gettext_lazy('Ceph集群已用存储容量TiB')
    OSD_IN_COUNT = 'osd_in_count', gettext_lazy('Ceph集群内OSD数')
    OSD_OUT = 'osd_out', gettext_lazy('Ceph集群外OSD信息')
    OSD_UP_COUNT = 'osd_up_count', gettext_lazy('Ceph集群活着且在运行OSD数')
    OSD_DOWN = 'osd_down', gettext_lazy('Ceph集群挂了且不再运行OSD信息')
    MON_STATUS = 'mon_status', gettext_lazy('mon状态')
    MGR_STATUS = 'mgr_status', gettext_lazy('mgr状态')
    POOL_META = 'pool_meta', gettext_lazy('Pool信息')
    PG_ACTIVE = 'pg_active', gettext_lazy('活动的PG信息')
    PG_UNACTIVE = 'pg_unactive', gettext_lazy('非活动的PG信息')
    PG_DEGRADED = 'pg_degraded', gettext_lazy('degraded降级PG信息')
    OBJ_DEGRADED = 'obj_degraded', gettext_lazy('degraded降级对象数量')
    OBJ_MISPLACED = 'obj_misplaced', gettext_lazy('misplaced存储错位对象数量')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class MonitorJobCephManager:
    backend = MonitorCephQueryAPI()

    tags_map = {
        CephQueryV2Choices.HEALTH_STATUS_DETAIL.value: backend.query_builder.tmpl_health_status_detail,
        CephQueryV2Choices.CLUSTER_SIZE.value: backend.query_builder.tmpl_total_bytes,
        CephQueryV2Choices.CLUSTER_USED_SIZE.value: backend.query_builder.tmpl_total_used_bytes,
        CephQueryV2Choices.OSD_IN_COUNT.value: backend.query_builder.tmpl_osd_in_count,
        CephQueryV2Choices.OSD_OUT.value: backend.query_builder.tmpl_osd_out,
        CephQueryV2Choices.OSD_UP_COUNT.value: backend.query_builder.tmpl_osd_up_count,
        CephQueryV2Choices.OSD_DOWN.value: backend.query_builder.tmpl_osd_down,
        CephQueryV2Choices.MON_STATUS.value: backend.query_builder.tmpl_mon_status,
        CephQueryV2Choices.MGR_STATUS.value: backend.query_builder.tmpl_mgr_status,
        CephQueryV2Choices.POOL_META.value: backend.query_builder.tmpl_pool_meta,
        CephQueryV2Choices.PG_ACTIVE.value: backend.query_builder.tmpl_pg_active,
        CephQueryV2Choices.PG_UNACTIVE.value: backend.query_builder.tmpl_pg_unactive,
        CephQueryV2Choices.PG_DEGRADED.value: backend.query_builder.tmpl_pg_degraded,
        CephQueryV2Choices.OBJ_DEGRADED.value: backend.query_builder.tmpl_obj_degraded,
        CephQueryV2Choices.OBJ_MISPLACED.value: backend.query_builder.tmpl_obj_misplaced,
    }

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobCeph.objects.select_related('org_data_center').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, monitor_unit: MonitorJobCeph):
        if tag == CephQueryChoices.ALL_TOGETHER.value:
            return self.query_together(monitor_unit=monitor_unit)

        return self._query(tag=tag, monitor_unit=monitor_unit)

    def query_together(self, monitor_unit: MonitorJobCeph):
        ret = {}
        tags = CephQueryChoices.values
        tags.remove(CephQueryChoices.ALL_TOGETHER.value)
        for tag in tags:
            try:
                data = self._query(tag=tag, monitor_unit=monitor_unit)
            except errors.Error as exc:
                data = []

            ret[tag] = data

        return ret

    def _query(self, tag: str, monitor_unit: MonitorJobCeph):
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
        provider = build_thanos_provider(monitor_unit.org_data_center)
        job_ceph_map = {monitor_unit.job_tag: monitor_unit}
        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_data(provider=provider, tag=tag, job=job.job_tag)
            if r:
                data = r[0]
                data['monitor'] = job_dict
            else:
                data = {'monitor': job_dict, 'value': None}

            ret_data.append(data)

        return ret_data

    def queryrange(self, tag: str, monitor_unit: MonitorJobCeph, start: int, end: int, step: int):
        provider = build_thanos_provider(monitor_unit.org_data_center)
        if tag == CephQueryChoices.ALL_TOGETHER.value:
            raise errors.InvalidArgument(message=_('范围查询不支持一起查询所有指标类型'))

        job_ceph_map = {monitor_unit.job_tag: monitor_unit}
        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_range_data(provider=provider, tag=tag, job=job.job_tag,
                                        start=start, end=end, step=step)
            if r:
                data = r[0]
                data.pop('metric', None)
                data['monitor'] = job_dict
            else:
                data = {'monitor': job_dict, 'values': []}

            ret_data.append(data)

        return ret_data

    def request_range_data(self, provider: ThanosProvider, tag: str, job: str, start: int, end: int, step: int):
        params = {'provider': provider, 'job': job, 'start': start, 'end': end, 'step': step}

        f = {
            CephQueryChoices.HEALTH_STATUS.value: self.backend.ceph_health_status_range,
            CephQueryChoices.CLUSTER_TOTAL_BYTES.value: self.backend.ceph_cluster_total_bytes_range,
            CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value: self.backend.ceph_cluster_total_used_bytes_range,
            CephQueryChoices.OSD_IN.value: self.backend.ceph_osd_in_range,
            CephQueryChoices.OSD_OUT.value: self.backend.ceph_osd_out_range,
            CephQueryChoices.OSD_UP.value: self.backend.ceph_osd_up_range,
            CephQueryChoices.OSD_DOWN.value: self.backend.ceph_osd_down_range
        }[tag]

        return f(**params)

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
            CephQueryChoices.HEALTH_STATUS.value: self.backend.ceph_health_status,
            CephQueryChoices.CLUSTER_TOTAL_BYTES.value: self.backend.ceph_cluster_total_bytes,
            CephQueryChoices.CLUSTER_TOTAL_USED_BYTES.value: self.backend.ceph_cluster_total_used_bytes,
            CephQueryChoices.OSD_IN.value: self.backend.ceph_osd_in,
            CephQueryChoices.OSD_OUT.value: self.backend.ceph_osd_out,
            CephQueryChoices.OSD_UP.value: self.backend.ceph_osd_up,
            CephQueryChoices.OSD_DOWN.value: self.backend.ceph_osd_down
        }[tag]

        return f(**params)

    def query_v2(self, tag: str, monitor_unit: MonitorJobCeph):
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
        job_dict = MonitorJobCephSerializer(monitor_unit).data
        if tag == CephQueryV2Choices.ALL_TOGETHER.value:
            data = self.async_query_together_v2(monitor_unit=monitor_unit)
        else:
            data = self._query_v2(tag=tag, monitor_unit=monitor_unit)

        data['monitor'] = job_dict
        return data

    def _query_v2(self, tag: str, monitor_unit: MonitorJobCeph):
        """
        :return:
            { tag: []}
        :raises: Error
        """
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tag_tmpl = self.tags_map[tag]
        r = self.backend.query_tag(endpoint_url=provider.endpoint_url, tag_tmpl=tag_tmpl, job=monitor_unit.job_tag)
        return {tag: r}

    def async_query_together_v2(self, monitor_unit: MonitorJobCeph):
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tags = CephQueryV2Choices.values
        tags.remove(CephQueryV2Choices.ALL_TOGETHER.value)

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

    async def req_tag(self, unit: MonitorJobCeph, endpoint_url: str, tag: str):
        try:
            tag_tmpl = self.tags_map[tag]
            ret = await self.backend.async_query_tag(
                endpoint_url=endpoint_url, tag_tmpl=tag_tmpl, job=unit.job_tag)
        except Exception as exc:
            err = Exception(f'{unit.name}, {endpoint_url}, {tag},{exc}')
            return tag, err

        return tag, ret
