from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from core import errors
from api.serializers import MonitorJobCephSerializer
from .models import MonitorJobCeph, MonitorProvider
from .backends.monitor_ceph import MonitorCephQueryAPI


class CephQueryChoices(models.TextChoices):
    HEALTH_STATUS = 'health_status', _('Ceph健康状态')
    CLUSTER_TOTAL_BYTES = 'cluster_total_bytes', _('Ceph集群存储容量')
    CLUSTER_TOTAL_USED_BYTES = 'cluster_total_used_bytes', _('Ceph集群已用存储容量')
    OSD_IN = 'osd_in', _('Ceph集群内OSD数')
    OSD_OUT = 'osd_out', _('Ceph集群外OSD数')
    OSD_UP = 'osd_up', _('Ceph集群活着且在运行OSD数')
    OSD_DOWN = 'osd_down', _('Ceph集群挂了且不再运行OSD数')


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
            raise errors.ConflictError(message=_('没有配置监控'))

        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_data(provider=job.provider, tag=tag, job=job.job_tag)
            data = r[0]
            data['monitor'] = job_dict
            ret_data.append(data)

        return ret_data

    def queryrange(self, tag: str, service_id: str, start: int, end: int, step: int):
        job_ceph_qs = self.get_queryset(service_id=service_id)
        job_ceph_map = {}
        for job in job_ceph_qs:
            job_ceph_map[job.job_tag] = job
        
        if len(job_ceph_map) == 0:
            raise errors.ConflictError(message=_('没有监控配置'))

        ret_data = []
        for job in job_ceph_map.values():
            job_dict = MonitorJobCephSerializer(job).data
            r = self.request_range_data(provider=job.provider, tag=tag, job=job.job_tag, start=start, end=end, step=step)
            if r:
                data = r[0]
                data.pop('metric', None)
                data['monitor'] = job_dict
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





