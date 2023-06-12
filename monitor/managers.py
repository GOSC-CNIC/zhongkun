from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.cache import cache as django_cache
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from core import errors
from api.serializers.monitor import (
    MonitorJobCephSerializer, MonitorJobServerSerializer
)
from .models import (
    MonitorJobCeph, MonitorProvider, MonitorJobServer, MonitorJobVideoMeeting,
    MonitorWebsite, MonitorWebsiteTask, MonitorWebsiteVersion, get_str_hash,
    WebsiteDetectionPoint, MonitorJobTiDB
)
from .backends.monitor_ceph import MonitorCephQueryAPI
from .backends.monitor_server import MonitorServerQueryAPI
from .backends.monitor_video_meeting import MonitorVideoMeetingQueryAPI
from .backends.monitor_website import MonitorWebsiteQueryAPI
from .backends.monitor_tidb import MonitorTiDBQueryAPI


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


class WebsiteQueryChoices(models.TextChoices):
    HTTP_STATUS_STATUS = 'http_status_code', _('请求状态码')
    DURATION_SECONDS = 'duration_seconds', _('请求耗时')
    HTTP_DURATION_SECONDS = 'http_duration_seconds', _('http请求各个部分耗时')


class TiDBQueryChoices(models.TextChoices):
    PD_NODES = 'pd_nodes', _('pd节点')
    TIDB_NODES = 'tidb_nodes', _('tidb节点')
    TIKV_NODES = 'tikv_nodes', _('tivk节点')
    CONNECTIONS_COUNT = 'connections_count', _('连接数')
    QPS = 'qps', _('每秒请求数')
    REGION_COUNT = 'region_count', _('副本数量')
    REGION_HEALTH = 'region_health', _('副本状态')
    STORAGE_CAPACITY = 'storage_capacity', _('存储总容量')
    CURRENT_STORAGE_SIZE = 'current_storage_size', _('当前存储容量')
    STORAGE = 'storage', _('存储总容量和当前已用容量')
    SERVER_CPU_USAGE = 'server_cpu_usage', _('主机CPU使用率')
    SERVER_MEM_USAGE = 'server_mem_usage', _('主机内存使用率')
    SERVER_DISK_USAGE = 'server_disk_usage', _('主机硬盘使用率')


class MonitorJobCephManager:
    backend = MonitorCephQueryAPI()

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobCeph.objects.select_related('provider').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, monitor_unit: MonitorJobCeph):
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
        job_ceph_map = {monitor_unit.job_tag: monitor_unit}
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

    def queryrange(self, tag: str, monitor_unit: MonitorJobCeph, start: int, end: int, step: int):
        job_ceph_map = {monitor_unit.job_tag: monitor_unit}
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

    def query(self, tag: str, monitor_unit: MonitorJobServer):
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
        job_server_map = {monitor_unit.job_tag: monitor_unit}
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

        if not job_video_meeting_map:
            raise errors.NoMonitorJob(message=_('没有监控配置'))

        ret_data = []
        job_dict = {
          "name": "科技云会节点监控",
          "name_en": "科技云会节点监控",
          "job_tag": "videomeeting",
        }

        provider = job_video_meeting_qs[0].provider
        job_tag = "shipinPing"
        r = self.request_data(provider=provider, tag=tag, job=job_tag)
        if r:
            for result in r:
                if result.get('metric').get('job') != job_tag:
                    continue

                hostname = result.get('metric').get('hostname')
                if hostname not in job_video_meeting_map:
                    continue

                job = job_video_meeting_map[hostname]
                ipv4s = [i.strip(' ') for i in job.ips.split(';')]
                item = {
                    'metric': {
                        'name': job.name,
                        'longitude': job.longitude,
                        'latitude': job.latitude,
                        'ipv4s': ipv4s
                    },
                    'value': result['value']
                }
                ret_data.append(item)

        return [{'monitor': job_dict, 'value': ret_data}]

    def request_data(self, provider: MonitorProvider, tag: str, job: str):
        """
        :return:
            [
                {
                    "metric": {
                        "__name__": "probe_success",
                        "hostname": "kongtianyuan",
                        "instance": "159.226.38.247:9115",
                        "job": "shipinPing",
                        "monitor": "example",
                        "receive_cluster": "network",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1637233827.692,
                        "0"
                    ]
                },
                {...}
            ]
        :raises: Error
        """
        params = {'provider': provider, 'job': job}
        f = {
            VideoMeetingQueryChoices.NODE_STATUS.value: self.backend.video_node_status,
            VideoMeetingQueryChoices.NODE_LATENCY.value: self.backend.video_node_lantency,
        }[tag]

        return f(**params)


class MonitorWebsiteManager:
    CACHE_KEY_DETECTION_POINT = 'monitor_website_detection_ponit_list'

    backend = MonitorWebsiteQueryAPI()

    @staticmethod
    def get_website_by_id(website_id: str) -> MonitorWebsite:
        return MonitorWebsite.objects.filter(id=website_id).first()

    @staticmethod
    def get_user_website(website_id: str, user):
        """
        查询用户的指定站点监控任务

        :raises: Error
        """
        website = MonitorWebsiteManager.get_website_by_id(website_id)
        if website is None:
            raise errors.NotFound(message=_('站点监控任务不存在。'))

        if website.user_id != user.id:
            raise errors.AccessDenied(message=_('无权限访问此站点监控任务。'))

        return website

    @staticmethod
    def add_website_task(
            name: str, scheme: str, hostname, uri: str, is_tamper_resistant: bool, remark: str, user_id: str):
        """
        :raises: Error
        """
        nt = timezone.now()
        user_website = MonitorWebsite(
            name=name, scheme=scheme, hostname=hostname, uri=uri, is_tamper_resistant=is_tamper_resistant,
            remark=remark, user_id=user_id, creation=nt, modification=nt
        )
        return MonitorWebsiteManager.do_add_website_task(user_website)

    @staticmethod
    def do_add_website_task(user_website: MonitorWebsite):
        """
        :raises: Error
        """
        full_url = user_website.full_url
        try:
            URLValidator()(full_url)
        except ValidationError as e:
            raise errors.InvalidArgument(message=_('网址无效'), code='InvalidUrl')

        user_website.url = full_url
        url_hash = get_str_hash(full_url)
        _website = MonitorWebsite.objects.filter(user_id=user_website.user_id, url_hash=url_hash).first()
        if _website is not None:
            raise errors.TargetAlreadyExists(message=_('已存在相同的网址。'))

        try:
            with transaction.atomic():
                version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                user_website.save(force_insert=True)

                # 监控任务表是否已存在相同网址，不存在就添加任务，更新任务版本
                task = MonitorWebsiteTask.objects.filter(url_hash=url_hash).first()
                if task is None:
                    task = MonitorWebsiteTask(url=full_url, is_tamper_resistant=user_website.is_tamper_resistant)
                    task.save(force_insert=True)
                    version.version_add_1()
                else:
                    # 用户监控任务标记防篡改，监控任务需要标记防篡改
                    if user_website.is_tamper_resistant and not task.is_tamper_resistant:
                        task.is_tamper_resistant = True
                        task.save(update_fields=['is_tamper_resistant'])
                        version.version_add_1()
        except Exception as exc:
            raise errors.Error(message=str(exc))

        return user_website

    @staticmethod
    def delete_website_task(_id: str, user):
        """
        :raises: Error
        """
        user_website: MonitorWebsite = MonitorWebsite.objects.filter(id=_id).first()
        if user_website is None:
            raise errors.NotFound(message=_('指定监控站点不存在。'))

        if user_website.user_id != user.id:
            raise errors.AccessDenied(message=_('无权限访问指定监控站点。'))

        MonitorWebsiteManager.do_delete_website_task(user_website)

    @staticmethod
    def do_delete_website_task(user_website: MonitorWebsite):
        full_url = user_website.full_url
        try:
            with transaction.atomic():
                version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                user_website.delete()
                # 除了要移除的站点，是否还有监控网址相同的 监控任务
                count = MonitorWebsite.objects.filter(url_hash=user_website.url_hash, url=full_url).count()
                if count == 0:
                    # 监控任务表移除任务，更新任务版本
                    MonitorWebsiteTask.objects.filter(url_hash=user_website.url_hash, url=full_url).delete()
                    version.version_add_1()
                else:
                    # 监控任务 防篡改 更新
                    changed = MonitorWebsiteManager._update_task_tamper_resistant(
                        url_hash=user_website.url_hash, full_url=full_url)
                    # 监控任务防篡改更新了，更新任务版本
                    if changed:
                        version.version_add_1()
        except Exception as exc:
            raise errors.Error(message=str(exc))

    @staticmethod
    def _update_task_tamper_resistant(url_hash: str, full_url: str):
        """
        :return:
            True    # 监控任务 防篡改 更新
            False   # 监控任务 防篡改 未更新
        """
        # 是否还有防篡改用户监控任务
        is_tamper_resistant = False
        sites = MonitorWebsite.objects.filter(
            url_hash=url_hash, is_tamper_resistant=True).all()
        for site in sites:
            site: MonitorWebsite
            if site.full_url == full_url:
                if site.is_tamper_resistant is True:
                    is_tamper_resistant = True
                    break

        # 尝试更新监控任务防篡改标记
        rows = MonitorWebsiteTask.objects.filter(
            url_hash=url_hash, url=full_url,
            is_tamper_resistant=not is_tamper_resistant).update(is_tamper_resistant=is_tamper_resistant)
        if rows > 0:
            return True

        return False

    @staticmethod
    def change_website_task(
            _id: str, user, name: str = '',
            scheme: str = '', hostname: str = '', uri: str = '', is_tamper_resistant: bool = None, remark: str = ''):
        """
        :raises: Error
        """
        user_website: MonitorWebsite = MonitorWebsite.objects.filter(id=_id).first()
        if user_website is None:
            raise errors.NotFound(message=_('指定监控站点不存在。'))

        if user_website.user_id != user.id:
            raise errors.AccessDenied(message=_('无权限访问指定监控站点。'))

        if name:
            user_website.name = name

        if remark:
            user_website.remark = remark

        if is_tamper_resistant is None:
            is_tamper_resistant = user_website.is_tamper_resistant

        MonitorWebsiteManager.do_change_website_task(
            user_website, new_scheme=scheme, new_hostname=hostname, new_uri=uri,
            new_tamper_resistant=is_tamper_resistant)

        return user_website

    @staticmethod
    def do_change_website_task(
            user_website: MonitorWebsite,
            new_scheme: str, new_hostname: str, new_uri: str, new_tamper_resistant: bool):
        """
        url有更改的任务处理，user_website对象会全更新
        """
        old_url = user_website.full_url
        old_is_tamper_resistant = user_website.is_tamper_resistant

        if new_scheme:
            user_website.scheme = new_scheme

        if new_hostname:
            user_website.hostname = new_hostname

        if new_uri:
            user_website.uri = new_uri

        new_url = user_website.full_url

        try:
            URLValidator()(new_url)
        except ValidationError as e:
            raise errors.InvalidArgument(message=_('网址无效'), code='InvalidUrl')

        user_website.url = new_url
        user_website.is_tamper_resistant = new_tamper_resistant

        # url有更改，可能需要修改监控任务表和版本编号
        if old_url != new_url or new_tamper_resistant != old_is_tamper_resistant:
            try:
                with transaction.atomic():
                    version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                    user_website.save(force_update=True)

                    # url未更改， 只是 防篡改标记 更改
                    if old_url == new_url:
                        # 监控任务 防篡改 更新
                        changed = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=user_website.url_hash, full_url=new_url)
                        if changed:
                            version.version_add_1()
                            return user_website

                    # --- url有更新，是否删除旧监控任务和增加新监控任务----

                    neet_change_version = False
                    # 修改站点地址后，是否还有旧监控网址相同的 监控任务
                    old_url_hash = get_str_hash(old_url)
                    count = MonitorWebsite.objects.filter(url_hash=old_url_hash, url=old_url).count()
                    if count == 0:
                        # 监控任务表移除任务，需要更新任务版本
                        MonitorWebsiteTask.objects.filter(url_hash=old_url_hash, url=old_url).delete()
                        neet_change_version = True
                    else:
                        # 监控任务 防篡改 更新
                        changed = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=old_url_hash, full_url=old_url)
                        if changed:
                            neet_change_version = True

                    # 修改站点地址后，是否需要增加新的监控网址 监控任务
                    new_url_hash = get_str_hash(new_url)
                    count = MonitorWebsiteTask.objects.filter(url_hash=new_url_hash, url=new_url).count()
                    if count == 0:
                        task = MonitorWebsiteTask(url=new_url, is_tamper_resistant=new_tamper_resistant)
                        task.save(force_insert=True)
                        neet_change_version = True
                    else:
                        # 监控任务 防篡改 更新
                        changed = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=new_url_hash, full_url=new_url)
                        if changed:
                            neet_change_version = True

                    if neet_change_version:
                        version.version_add_1()
            except Exception as exc:
                raise errors.Error(message=str(exc))
        else:
            try:
                user_website.save(force_update=True)
            except Exception as exc:
                raise errors.Error(message=str(exc))

        return user_website

    @staticmethod
    def get_user_website_queryset(user_id: str):
        return MonitorWebsite.objects.select_related('user').filter(user_id=user_id).all()

    @staticmethod
    def get_detection_ponits() -> dict:
        """
        查询所有探测点
        """
        _key = MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT
        dict_dps = django_cache.get(_key)
        if dict_dps is None:
            queryset = WebsiteDetectionPoint.objects.select_related('provider').all()
            dict_dps = {point.id: point for point in queryset}
            django_cache.set(_key, dict_dps, 120)

        return dict_dps

    def get_detection_ponit(self, dp_id: str):
        """
        查询指定的探测点实例

        :param dp_id: 探测点id; None or '' 时选择一个可用的
        """
        dict_dps = self.get_detection_ponits()
        detection_ponit = dict_dps.get(dp_id)
        if not detection_ponit:
            raise errors.NotFound(message=_('网站监控探测点不存在。'), code='NoSuchDetectionPoint')

        if not detection_ponit.enable:
            raise errors.ConflictError(message=_('网站监控探测点暂未启用。'))

        if not detection_ponit.provider:
            raise errors.ConflictError(message=_('探测点未配置监控数据查询服务信息。'))

        return detection_ponit

    def query(self, website: MonitorWebsite, tag: str, dp_id: str):
        """
        :raises: Error
        """
        detection_point = self.get_detection_ponit(dp_id=dp_id)
        provider = detection_point.provider
        return self.request_data(provider=provider, tag=tag, url=website.full_url)

    def request_data(self, provider: MonitorProvider, tag: str, url: str):
        """
        :return:
            [
                {
                    "metric": {
                        "__name__": "probe_success",
                        "hostname": "kongtianyuan",
                        "instance": "159.226.38.247:9115",
                        "job": "shipinPing",
                        "monitor": "example",
                        "receive_cluster": "network",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "value": [
                        1637233827.692,
                        "0"
                    ]
                },
                {...}
            ]
        :raises: Error
        """
        params = {'provider': provider, 'url': url}
        f = {
            WebsiteQueryChoices.HTTP_STATUS_STATUS.value: self.backend.http_status_code_period,
            WebsiteQueryChoices.DURATION_SECONDS.value: self.backend.duration_seconds_period,
            WebsiteQueryChoices.HTTP_DURATION_SECONDS.value: self.backend.http_duration_seconds_period
        }[tag]

        return f(**params)

    def query_range(self, website: MonitorWebsite, tag: str, start: int, end: int, step: int, dp_id: str):
        """
        :raises: Error
        """
        detection_point = self.get_detection_ponit(dp_id=dp_id)
        provider = detection_point.provider
        return self.request_range_data(
            provider=provider, tag=tag, url=website.full_url, start=start, end=end, step=step)

    def request_range_data(self, provider: MonitorProvider, tag: str, url: str, start: int, end: int, step: int):
        """
        :return:
            [
                {
                    "metric": {
                        "__name__": "probe_success",
                        "hostname": "kongtianyuan",
                        "instance": "159.226.38.247:9115",
                        "job": "shipinPing",
                        "monitor": "example",
                        "receive_cluster": "network",
                        "receive_replica": "0",
                        "tenant_id": "default-tenant"
                    },
                    "values": [
                        [1637233827.692, "0"]
                    ]
                },
                {...}
            ]
        :raises: Error
        """
        params = {'provider': provider, 'url': url, 'start': start, 'end': end, 'step': step}
        f = {
            WebsiteQueryChoices.HTTP_STATUS_STATUS.value: self.backend.http_status_code_range,
            WebsiteQueryChoices.DURATION_SECONDS.value: self.backend.duration_seconds_range,
            WebsiteQueryChoices.HTTP_DURATION_SECONDS.value: self.backend.http_duration_seconds_range
        }[tag]

        return f(**params)


class MonitorJobTiDBManager:
    backend = MonitorTiDBQueryAPI()

    @staticmethod
    def get_queryset(service_id: str = None):
        qs = MonitorJobTiDB.objects.select_related('provider').all()
        if service_id:
            qs = qs.filter(service_id=service_id)

        return qs

    def query(self, tag: str, monitor_unit: MonitorJobTiDB):
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
        job_dict = MonitorJobCephSerializer(monitor_unit).data
        r = self.request_data(provider=monitor_unit.provider, tag=tag, job=monitor_unit.job_tag)
        for data in r:
            data['monitor'] = job_dict
            ret_data.append(data)

        return ret_data

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
