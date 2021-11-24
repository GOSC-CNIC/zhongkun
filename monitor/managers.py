from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from core import errors
from api.serializers import MonitorJobCephSerializer, MonitorJobServerSerializer, MonitorJobVideoMeetingSerializer
from .models import MonitorJobCeph, MonitorProvider, MonitorJobServer, MonitorJobVideoMeeting
from .backends.monitor_ceph import MonitorCephQueryAPI
from .backends.monitor_server import MonitorServerQueryAPI
from .backends.monitor_video_meeting import MonitorVideoMeetingQueryAPI


class CephQueryChoices(models.TextChoices):
    HEALTH_STATUS = 'health_status', _('Ceph健康状态')
    CLUSTER_TOTAL_BYTES = 'cluster_total_bytes', _('Ceph集群存储容量')
    CLUSTER_TOTAL_USED_BYTES = 'cluster_total_used_bytes', _('Ceph集群已用存储容量')
    OSD_IN = 'osd_in', _('Ceph集群内OSD数')
    OSD_OUT = 'osd_out', _('Ceph集群外OSD数')
    OSD_UP = 'osd_up', _('Ceph集群活着且在运行OSD数')
    OSD_DOWN = 'osd_down', _('Ceph集群挂了且不再运行OSD数')


class ServerQueryChoices(models.TextChoices):
    HOST_COUNT = 'host_count', _('主机数量')
    HOST_UP_COUNT = 'host_up_count', _('在线主机数量')
    HEALTH_STATUS = 'health_status', _('主机集群健康状态')
    CPU_USAGE = 'cpu_usage', _('集群平均CPU使用率')
    MEM_USAGE = 'mem_usage', _('集群平均内存使用率')
    DISK_USAGE = 'disk_usage', _('集群平均磁盘使用率')
    MIN_CPU_USAGE = 'min_cpu_usage', _('集群最小CPU使用率')
    MAX_CPU_USAGE = 'max_cpu_usage', _('集群最大CPU使用率')
    MIN_MEM_USAGE = 'min_mem_usage', _('集群最小内存使用率')
    MAX_MEM_USAGE = 'max_mem_usage', _('集群最大内存使用率')
    MIN_DISK_USAGE = 'min_disk_usage', _('集群最小磁盘使用率')
    MAX_DISK_USAGE = 'max_disk_usage', _('集群最大磁盘使用率')


class VideoMeetingQueryChoices(models.TextChoices):
    NODE_STATUS = 'node_status', _('节点在线状态')
    NODE_LATENCY = 'node_lantency', _('节点延迟')


class MonitorJobCephManager:
    backend = MonitorCephQueryAPI()

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobCeph.objects.select_related('provider').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, service_id: str):
        """
        :return:
            [
                {
                    "monitor":{
                        "name": "",
                        "name_en": "",
                        "job_tag": "",
                        "service_id": "",
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
        job_ceph_qs = self.get_queryset(service_id=service_id)
        job_ceph_map = {}
        for job in job_ceph_qs:
            job_ceph_map[job.job_tag] = job

        if len(job_ceph_map) == 0:
            raise errors.NoMonitorJob(message=_('没有配置监控'))

        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_data(provider=job.provider, tag=tag, job=job.job_tag)
            if r:
                data = r[0]
                data['monitor'] = job_dict
            else:
                data = {'monitor': job_dict, 'value': None}

            ret_data.append(data)

        return ret_data

    def queryrange(self, tag: str, service_id: str, start: int, end: int, step: int):
        job_ceph_qs = self.get_queryset(service_id=service_id)
        job_ceph_map = {}
        for job in job_ceph_qs:
            job_ceph_map[job.job_tag] = job

        if len(job_ceph_map) == 0:
            raise errors.NoMonitorJob(message=_('没有监控配置'))

        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_range_data(provider=job.provider, tag=tag, job=job.job_tag,
                                        start=start, end=end, step=step)
            if r:
                data = r[0]
                data.pop('metric', None)
                data['monitor'] = job_dict
            else:
                data = {'monitor': job_dict, 'values': []}

            ret_data.append(data)

        return ret_data

    def request_range_data(self, provider: MonitorProvider, tag: str, job: str, start: int, end: int, step: int):
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

    def request_data(self, provider: MonitorProvider, tag: str, job: str):
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


class MonitorJobServerManager:
    backend = MonitorServerQueryAPI()

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobServer.objects.select_related('provider').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, service_id: str):
        """
        :return:
            [
                {
                    "monitor": {
                        "name": "大规模对象存储云主机服务物理服务器监控",
                        "name_en": "大规模对象存储云主机服务物理服务器监控",
                        "job_tag": "obs-node",
                        "service_id": "1",
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
        job_server_qs = self.get_queryset(service_id=service_id)
        job_server_map = {}
        for job in job_server_qs:
            job_server_map[job.job_tag] = job

        if len(job_server_map) == 0:
            raise errors.NoMonitorJob(message=_('没有配置监控'))

        ret_data = []

        for job in job_server_map.values():
            job_dict = MonitorJobServerSerializer(job).data
            r = self.request_data(provider=job.provider, tag=tag, job=job.job_tag)
            if r:
                data = r[0]
                data.pop('metric', None)
                data['monitor'] = job_dict
            else:
                data = {'monitor': job_dict, 'value': None}

            ret_data.append(data)

        return ret_data

    def request_data(self, provider: MonitorProvider, tag: str, job: str):
        """
        :return:
        :raises: Error
        """
        params = {'provider': provider, 'job': job}
        f = {
            ServerQueryChoices.HEALTH_STATUS.value: self.backend.server_health_status,
            ServerQueryChoices.HOST_COUNT.value: self.backend.server_host_count,
            ServerQueryChoices.HOST_UP_COUNT.value: self.backend.server_host_up_count,
            ServerQueryChoices.CPU_USAGE.value: self.backend.server_cpu_usage,
            ServerQueryChoices.MEM_USAGE.value: self.backend.server_mem_usage,
            ServerQueryChoices.DISK_USAGE.value: self.backend.server_disk_usage,
            ServerQueryChoices.MIN_CPU_USAGE.value: self.backend.server_min_cpu_usage,
            ServerQueryChoices.MAX_CPU_USAGE.value: self.backend.server_max_cpu_usage,
            ServerQueryChoices.MIN_MEM_USAGE.value: self.backend.server_min_mem_usage,
            ServerQueryChoices.MAX_MEM_USAGE.value: self.backend.server_max_mem_usage,
            ServerQueryChoices.MIN_DISK_USAGE.value: self.backend.server_min_disk_usage,
            ServerQueryChoices.MAX_DISK_USAGE.value: self.backend.server_max_disk_usage,
        }[tag]

        return f(**params)


class MonitorJobVideoMeetingManager:
    backend = MonitorVideoMeetingQueryAPI()

    @staticmethod
    def get_queryset():
        qs = MonitorJobVideoMeeting.objects.select_related('provider').all()
        return qs

    def query(self, tag):
        job_video_meeting_qs = self.get_queryset()
        job_video_meeting_map = {}
        for job in job_video_meeting_qs:
            job_video_meeting_map[job.job_tag] = job

        if len(job_video_meeting_map) == 0:
            raise errors.NoMonitorJob(message=_('没有监控配置'))

        ret_data = []
        job_dict = {
          "name": "科技云会节点监控",
          "name_en": "科技云会节点监控",
          "job_tag": "videomeeting",
        }
        for job in job_video_meeting_map.values():
            # 由于没有service_id所以job_dict无法生效
            # job_dict = MonitorJobVideoMeetingSerializer(job).data

            r = self.request_data(provider=job.provider, tag=tag)
            if r:
                #  [
                #     {
                #         "metric": {
                #             "__name__": "probe_success",
                #             "hostname": "kongtianyuan",
                #             "instance": "159.226.38.247:9115",
                #             "job": "shipinPing",
                #             "monitor": "example",
                #             "receive_cluster": "network",
                #             "receive_replica": "0",
                #             "tenant_id": "default-tenant"
                #         },
                #         "value": [
                #             1637233827.692,
                #             "0"
                #         ]
                #     },
                #     {...}
                # ]

                for result in r:
                    if result.get('metric').get('job') != "shipinPing":
                        continue
                    hostname = result.get('metric').get('hostname')
                    result.pop('metric')
                    qs = job_video_meeting_qs.filter(job_tag=hostname).first()
                    if qs:
                        result['metric'] = {
                            'name': qs.name,
                            'longitude': qs.longitude,
                            'latitude': qs.latitude
                        }
                        ret_data.append(result)
                return [{'monitor': job_dict, 'value': ret_data}]
            else:
                return [{'monitor': job_dict, 'value': None}]

    def request_data(self, provider: MonitorProvider, tag):
        """
        :return:
        :raises: Error
        """
        params = {'provider': provider}
        f = {
            VideoMeetingQueryChoices.NODE_STATUS.value: self.backend.video_node_status,
            VideoMeetingQueryChoices.NODE_LATENCY.value: self.backend.video_node_lantency,
        }[tag]

        return f(**params)
