import asyncio

from django.db import models
from django.utils.translation import gettext_lazy

from apps.monitor.utils import build_thanos_provider
from apps.monitor.serializers import MonitorJobServerSerializer
from apps.monitor.models import MonitorJobServer
from apps.monitor.backends.monitor_server import MonitorServerQueryAPI


class ServerQueryChoices(models.TextChoices):
    HOST_COUNT = 'host_count', gettext_lazy('主机数量')
    HOST_UP_COUNT = 'host_up_count', gettext_lazy('在线主机数量')
    HEALTH_STATUS = 'health_status', gettext_lazy('主机集群健康状态')
    CPU_USAGE = 'cpu_usage', gettext_lazy('集群平均CPU使用率')
    MEM_USAGE = 'mem_usage', gettext_lazy('集群平均内存使用率')
    DISK_USAGE = 'disk_usage', gettext_lazy('集群平均磁盘使用率')
    MIN_CPU_USAGE = 'min_cpu_usage', gettext_lazy('集群最小CPU使用率')
    MAX_CPU_USAGE = 'max_cpu_usage', gettext_lazy('集群最大CPU使用率')
    MIN_MEM_USAGE = 'min_mem_usage', gettext_lazy('集群最小内存使用率')
    MAX_MEM_USAGE = 'max_mem_usage', gettext_lazy('集群最大内存使用率')
    MIN_DISK_USAGE = 'min_disk_usage', gettext_lazy('集群最小磁盘使用率')
    MAX_DISK_USAGE = 'max_disk_usage', gettext_lazy('集群最大磁盘使用率')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class ServerQueryV2Choices(models.TextChoices):
    HOST_UP = 'host_up', gettext_lazy('在线主机')
    HOST_DOWN = 'host_down', gettext_lazy('掉线主机')
    HOST_BOOT_TIME = 'boot_time', gettext_lazy('主机启动时间(天)')
    HOST_CPU_COUNT = 'host_cpu_count', gettext_lazy('主机CPU核数')
    HOST_CPU_USAGE = 'host_cpu_usage', gettext_lazy('主机CPU使用率')
    HOST_MEM_SIZE = 'host_mem_size', gettext_lazy('主机内存大小(GiB)')
    HOST_MEM_AVAIL = 'host_mem_avail', gettext_lazy('主机可用内存大小(GiB)')
    HOST_ROOT_DIR_SIZE = 'root_dir_size', gettext_lazy('主机根目录容量(GiB)')
    HOST_ROOT_DIR_AVAIL_SIZE = 'root_dir_avail_size', gettext_lazy('主机根目录可用容量(GiB)')
    HOST_NET_RATE_IN = 'net_rate_in', gettext_lazy('下行接收带宽(MiB/s)')
    HOST_NET_RATE_OUT = 'net_rate_out', gettext_lazy('上行发送带宽(MiB/s)')
    ALL_TOGETHER = 'all_together', gettext_lazy('一起查询所有指标')


class MonitorJobServerManager:
    backend = MonitorServerQueryAPI()
    v1_tag_tmpl_map = {
        ServerQueryChoices.HOST_COUNT.value: backend.query_builder.server_host_count,
        ServerQueryChoices.HOST_UP_COUNT.value: backend.query_builder.server_host_up_count,
        ServerQueryChoices.HEALTH_STATUS.value: backend.query_builder.server_health_status,
        ServerQueryChoices.CPU_USAGE.value: backend.query_builder.server_cpu_usage,
        ServerQueryChoices.MEM_USAGE.value: backend.query_builder.server_mem_usage,
        ServerQueryChoices.DISK_USAGE.value: backend.query_builder.server_disk_usage,
        ServerQueryChoices.MIN_CPU_USAGE.value: backend.query_builder.server_min_cpu_usage,
        ServerQueryChoices.MAX_CPU_USAGE.value: backend.query_builder.server_max_cpu_usage,
        ServerQueryChoices.MIN_MEM_USAGE.value: backend.query_builder.server_min_mem_usage,
        ServerQueryChoices.MAX_MEM_USAGE.value: backend.query_builder.server_max_mem_usage,
        ServerQueryChoices.MIN_DISK_USAGE.value: backend.query_builder.server_min_disk_usage,
        ServerQueryChoices.MAX_DISK_USAGE.value: backend.query_builder.server_max_disk_usage
    }

    v2_tag_tmpl_map = {
        ServerQueryV2Choices.HOST_UP.value: backend.query_builder.tmpl_up,
        ServerQueryV2Choices.HOST_DOWN.value: backend.query_builder.tmpl_down,
        ServerQueryV2Choices.HOST_BOOT_TIME.value: backend.query_builder.tmpl_boot_time,
        ServerQueryV2Choices.HOST_CPU_COUNT.value: backend.query_builder.tmpl_cpu_count,
        ServerQueryV2Choices.HOST_CPU_USAGE.value: backend.query_builder.tmpl_cpu_usage,
        ServerQueryV2Choices.HOST_MEM_SIZE.value: backend.query_builder.tmpl_mem_size,
        ServerQueryV2Choices.HOST_MEM_AVAIL.value: backend.query_builder.tmpl_mem_availabele,
        ServerQueryV2Choices.HOST_ROOT_DIR_SIZE.value: backend.query_builder.tmpl_root_dir_size,
        ServerQueryV2Choices.HOST_ROOT_DIR_AVAIL_SIZE.value: backend.query_builder.tmpl_root_dir_avail_size,
        ServerQueryV2Choices.HOST_NET_RATE_IN.value: backend.query_builder.tmpl_net_rate_in,
        ServerQueryV2Choices.HOST_NET_RATE_OUT.value: backend.query_builder.tmpl_net_rate_out
    }

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobServer.objects.select_related('org_data_center').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, monitor_unit: MonitorJobServer):
        if tag == ServerQueryChoices.ALL_TOGETHER.value:
            return self.query_together(monitor_unit=monitor_unit)

        return self._query(tag=tag, monitor_unit=monitor_unit)

    def query_together(self, monitor_unit: MonitorJobServer):
        tags = ServerQueryChoices.values
        tags.remove(ServerQueryChoices.ALL_TOGETHER.value)
        provider = build_thanos_provider(monitor_unit.org_data_center)
        unit_meta = MonitorJobServerSerializer(monitor_unit).data
        tasks = [
            self.req_tag(
                unit=monitor_unit, endpoint_url=provider.endpoint_url, tag=tag, tag_tmpl=self.v1_tag_tmpl_map[tag]
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
                if tag_data:
                    tag_data[0]['monitor'] = unit_meta

                data[tag] = tag_data

        if errs:
            data['errors'] = errs

        return data

    def _query(self, tag: str, monitor_unit: MonitorJobServer):
        """
        :return:
            [
                {
                    "monitor": {
                        "name": "大规模对象存储云主机服务物理服务器监控",
                        "name_en": "大规模对象存储云主机服务物理服务器监控",
                        "job_tag": "obs-node",
                        "id": "xxx",
                        "creation": "2021-10-28T02:09:37.639453Z"
                    },
                    "value": [
                        1631585555,
                        "13"
                    ]
                }
            ]
        :raises: Error
        """
        provider = build_thanos_provider(monitor_unit.org_data_center)
        ret_data = []
        job_dict = MonitorJobServerSerializer(monitor_unit).data
        tag_tmpl = self.v1_tag_tmpl_map[tag]
        r = self.backend.query_tag(endpoint_url=provider.endpoint_url, tag_tmpl=tag_tmpl, job=monitor_unit.job_tag)
        if r:
            data = r[0]
            data.pop('metric', None)
            data['monitor'] = job_dict
        else:
            data = {'monitor': job_dict, 'value': None}

        ret_data.append(data)
        return ret_data

    def query_v2(self, tag: str, monitor_unit: MonitorJobServer):
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
        job_dict = MonitorJobServerSerializer(monitor_unit).data
        if tag == ServerQueryV2Choices.ALL_TOGETHER.value:
            data = self.async_query_together_v2(monitor_unit=monitor_unit)
        else:
            data = self._query_v2(tag=tag, monitor_unit=monitor_unit)

        data['monitor'] = job_dict
        return data

    def _query_v2(self, tag: str, monitor_unit: MonitorJobServer):
        """
        :return:
            { tag: []}
        :raises: Error
        """
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tag_tmpl = self.v2_tag_tmpl_map[tag]
        r = self.backend.query_tag(endpoint_url=provider.endpoint_url, tag_tmpl=tag_tmpl, job=monitor_unit.job_tag)
        return {tag: r}

    def async_query_together_v2(self, monitor_unit: MonitorJobServer):
        provider = build_thanos_provider(monitor_unit.org_data_center)
        tags = ServerQueryV2Choices.values
        tags.remove(ServerQueryV2Choices.ALL_TOGETHER.value)

        tasks = [
            self.req_tag(
                unit=monitor_unit, endpoint_url=provider.endpoint_url, tag=tag, tag_tmpl=self.v2_tag_tmpl_map[tag]
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

    async def req_tag(self, unit: MonitorJobServer, endpoint_url: str, tag: str, tag_tmpl: str):
        try:
            ret = await self.backend.async_query_tag(
                endpoint_url=endpoint_url, tag_tmpl=tag_tmpl, job=unit.job_tag)
        except Exception as exc:
            err = Exception(f'{unit.name}, {endpoint_url}, {tag},{exc}')
            return tag, err

        return tag, ret
