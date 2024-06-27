import math
from urllib.parse import urlsplit

from django.db import models, transaction
from django.utils.translation import gettext_lazy, gettext as _
from django.utils import timezone
from django.core.cache import cache as django_cache
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

from core import errors
from apps.service.odc_manager import OrgDataCenterManager
from apps.monitor.models import (
    MonitorProvider, MonitorJobVideoMeeting,
    MonitorWebsite, MonitorWebsiteTask, MonitorWebsiteVersion, get_str_hash,
    WebsiteDetectionPoint, MonitorWebsiteRecord
)
from apps.monitor.backends.monitor_video_meeting import MonitorVideoMeetingQueryAPI
from apps.monitor.backends.monitor_website import MonitorWebsiteQueryAPI
from apps.monitor.managers.probe_task import ProbeTaskClient


class VideoMeetingQueryChoices(models.TextChoices):
    NODE_STATUS = 'node_status', gettext_lazy('节点在线状态')
    NODE_LATENCY = 'node_lantency', gettext_lazy('节点延迟')


class WebsiteQueryChoices(models.TextChoices):
    SUCCESS = 'success', gettext_lazy('tcp或http是否成功')
    DURATION_SECONDS = 'duration_seconds', gettext_lazy('tcp或http请求耗时')
    HTTP_STATUS_STATUS = 'http_status_code', gettext_lazy('http请求状态码')
    HTTP_DURATION_SECONDS = 'http_duration_seconds', gettext_lazy('http请求各个部分耗时')


class URLTCPValidator(URLValidator):

    schemes = ["http", "https", "tcp"]


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
    def parse_http_url(http_url: str):
        """
        HttPs://User:passWd@Host:port/a/b?c=1&d=6#frag -> (https://, User:passWd@Host:port, /a/b?c=1&d=6#frag)
        https://user:passwd@host:port/a/b?c=1&d=6#frag -> (https://, user:passwd@host:port, /a/b?c=1&d=6#frag)
        https://host:port/a/b?c=1#frag -> (https://, host:port, /a/b?c=1#frag)
        https://host/a/b?c=1#frag -> (https://, host, /a/b?c=1#frag)
        https://host/a/b? -> (https://, host, /a/b)
        https://host/ -> (https://, host, /)
        https://host -> (https://, host, '')
        https://host/?c=1#frag -> (https://, host, /?c=1#frag)
        https://host?c=1#frag -> (https://, host, ?c=1#frag)
        https://host?c=t测试&d=6#frag -> (https://, host, ?c=t测试&d=6#frag)
        https://host/tes测试/b -> (https://, host, /tes测试/b)
        """
        items = urlsplit(http_url)
        scheme, netloc, url, query, fragment = items
        scheme = scheme.lower() + '://'
        hostname = netloc

        uri = url
        if url and url[:1] != '/':
            uri = '/' + url

        if query:
            uri = uri + '?' + query

        if fragment:
            uri = uri + '#' + fragment

        return scheme, hostname, uri

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
    def get_user_readable_website(website_id: str, user):
        """
        查询用户有访问权限的指定站点监控任务

        :raises: Error
        """
        website = MonitorWebsiteManager.get_website_by_id(website_id)
        if website is None:
            raise errors.NotFound(message=_('站点监控任务不存在。'))

        if website.user_id and website.user_id == user.id:
            pass
        elif website.odc_id and OrgDataCenterManager.is_admin_of_odc(odc_id=website.odc_id, user_id=user.id):
            pass
        else:
            raise errors.AccessDenied(message=_('无权限访问此站点监控任务。'))

        return website

    @staticmethod
    def get_user_website_queryset(user_id: str, scheme: str = None):
        """
        scheme: one in [None, http, tcp]
        """
        q = models.Q(user_id=user_id) | models.Q(odc__users__id=user_id)
        if scheme:
            q = q & models.Q(scheme__startswith=scheme.lower())

        return MonitorWebsite.objects.select_related('user', 'odc').filter(q).distinct()

    @staticmethod
    def get_user_http_task_qs(user):
        """
        查询用户的所有站点监控任务

        :raises: Error
        """
        return MonitorWebsiteManager.get_user_website_queryset(user_id=user.id, scheme='http')

    @staticmethod
    def get_user_tcp_task_qs(user):
        """
        查询用户的所有ftp监控任务

        :raises: Error
        """
        return MonitorWebsiteManager.get_user_website_queryset(user_id=user.id, scheme='tcp')

    @staticmethod
    def add_website_task(
            name: str, scheme: str, hostname, uri: str, is_tamper_resistant: bool, remark: str,
            user_id, odc_id=None):
        """
        :raises: Error
        """
        nt = timezone.now()
        user_website = MonitorWebsite(
            name=name, scheme=scheme, hostname=hostname, uri=uri, is_tamper_resistant=is_tamper_resistant,
            remark=remark, user_id=user_id, odc_id=odc_id, creation=nt, modification=nt
        )
        return MonitorWebsiteManager.do_add_website_task(user_website)

    @staticmethod
    def do_add_website_task(user_website: MonitorWebsite):
        """
        :raises: Error
        """
        full_url = user_website.full_url
        try:
            URLTCPValidator()(full_url)
        except ValidationError as e:
            raise errors.InvalidArgument(message=_('网址无效'), code='InvalidUrl')

        url_hash = get_str_hash(full_url)
        _website = MonitorWebsite.objects.filter(user_id=user_website.user_id, url_hash=url_hash).first()
        if _website is not None:
            raise errors.TargetAlreadyExists(message=_('已存在相同的网址。'))

        try:
            probe_tasks = []
            with transaction.atomic():
                version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                user_website.save(force_insert=True)

                # 监控任务表是否已存在相同网址，不存在就添加任务，更新任务版本
                task = MonitorWebsiteTask.objects.filter(url_hash=url_hash).first()
                if task is None:
                    task = MonitorWebsiteTask(url=full_url, is_tamper_resistant=user_website.is_tamper_resistant)
                    task.save(force_insert=True)
                    version.version_add_1()
                    # 同步到探测点服务的任务
                    probes_dict = MonitorWebsiteManager.get_detection_ponits(enable=True)
                    for probe in probes_dict.values():
                        probe_tasks.append(ProbeTaskClient(probe=probe).add_task_to_probe(
                            web_url=full_url, url_hash=user_website.url_hash,
                            is_tamper_resistant=user_website.is_tamper_resistant, version=version.version
                        ))
                else:
                    # 用户监控任务标记防篡改，监控任务需要标记防篡改
                    task_old_is_tamper_resistant = task.is_tamper_resistant
                    if user_website.is_tamper_resistant and not task_old_is_tamper_resistant:
                        task.is_tamper_resistant = True
                        task.save(update_fields=['is_tamper_resistant'])
                        version.version_add_1()
                        # 同步到探测点服务的任务
                        probes_dict = MonitorWebsiteManager.get_detection_ponits(enable=True)
                        for probe in probes_dict.values():
                            probe_tasks.append(ProbeTaskClient(probe=probe).change_task_to_probe(
                                web_url=full_url, url_hash=user_website.url_hash,
                                is_tamper_resistant=task_old_is_tamper_resistant,
                                new_web_url=full_url, new_url_hash=user_website.url_hash,
                                new_is_tamper_resistant=True,
                                version=version.version
                            ))

            if probe_tasks:
                ProbeTaskClient.do_async_probe_tasks(tasks=probe_tasks)

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

        if not user_website.user_id or user_website.user_id != user.id:
            raise errors.AccessDenied(message=_('无权限访问指定监控站点。'))

        MonitorWebsiteManager.do_delete_website_task(user_website)

    @staticmethod
    def do_delete_website_task(user_website: MonitorWebsite):
        full_url = user_website.full_url
        try:
            probe_tasks = []
            with transaction.atomic():
                version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                user_website.delete()
                # 站点监控删除记录
                MonitorWebsiteRecord.create_record_for_website(site=user_website)
                # 除了要移除的站点，是否还有监控网址相同的 监控任务
                count = MonitorWebsite.objects.filter(url_hash=user_website.url_hash).count()
                if count == 0:
                    # 监控任务表移除任务，更新任务版本
                    MonitorWebsiteTask.objects.filter(url_hash=user_website.url_hash, url=full_url).delete()
                    version.version_add_1()

                    # 同步到探测点服务的任务
                    probes_dict = MonitorWebsiteManager.get_detection_ponits(enable=True)
                    for probe in probes_dict.values():
                        probe_tasks.append(ProbeTaskClient(probe=probe).remove_task_from_probe(
                            web_url=full_url, url_hash=user_website.url_hash,
                            is_tamper_resistant=user_website.is_tamper_resistant, version=version.version
                        ))
                else:
                    # 监控任务 防篡改 更新
                    changed, task_now_tamper = MonitorWebsiteManager._update_task_tamper_resistant(
                        url_hash=user_website.url_hash, full_url=full_url)
                    # 监控任务防篡改更新了，更新任务版本
                    if changed:
                        version.version_add_1()
                        # 同步到探测点服务的任务
                        probes_dict = MonitorWebsiteManager.get_detection_ponits(enable=True)
                        for probe in probes_dict.values():
                            probe_tasks.append(ProbeTaskClient(probe=probe).change_task_to_probe(
                                web_url=full_url, url_hash=user_website.url_hash,
                                is_tamper_resistant=user_website.is_tamper_resistant,
                                new_web_url=full_url, new_url_hash=user_website.url_hash,
                                new_is_tamper_resistant=task_now_tamper,
                                version=version.version
                            ))

            if probe_tasks:
                ProbeTaskClient.do_async_probe_tasks(tasks=probe_tasks)

        except Exception as exc:
            raise errors.Error(message=str(exc))

    @staticmethod
    def _update_task_tamper_resistant(url_hash: str, full_url: str):
        """
        :return:(
            change: bool,        # True(监控任务 防篡改 发生更新)，False(监控任务 防篡改 未更新)
            is_tamper_resistant: bool    # 当前监控任务 防篡改 应该的状态
        )
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
            return True, is_tamper_resistant

        return False, is_tamper_resistant

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

        if user_website.user_id:
            if user_website.user_id != user.id:
                raise errors.AccessDenied(message=_('无权限访问指定监控任务。'))
        elif user_website.odc_id:
            raise errors.AccessDenied(message=_('数据中心监控任务不允许修改。'))
        else:
            raise errors.AccessDenied(message=_('无权限访问指定监控任务。'))

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
            URLTCPValidator()(new_url)
        except ValidationError as e:
            raise errors.InvalidArgument(message=_('网址无效'), code='InvalidUrl')

        new_url_hash = get_str_hash(new_url)
        _website = MonitorWebsite.objects.filter(
            user_id=user_website.user_id, url_hash=new_url_hash
        ).exclude(id=user_website.id).first()
        if _website is not None:
            raise errors.TargetAlreadyExists(message=_('已存在相同的网址。'))

        user_website.is_tamper_resistant = new_tamper_resistant

        # url有更改，可能需要修改监控任务表和版本编号
        if old_url != new_url or new_tamper_resistant != old_is_tamper_resistant:
            try:
                probe_tasks = []
                probes_dict = MonitorWebsiteManager.get_detection_ponits(enable=True)
                with transaction.atomic():
                    version = MonitorWebsiteVersion.get_instance(select_for_update=True)
                    user_website.save(force_update=True)

                    # url未更改， 只是 防篡改标记 更改
                    if old_url == new_url:
                        # 监控任务 防篡改 更新
                        changed, task_now_tamper = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=user_website.url_hash, full_url=new_url)
                        if changed:
                            version.version_add_1()
                            # 同步到探测点服务的任务
                            for probe in probes_dict.values():
                                probe_tasks.append(ProbeTaskClient(probe=probe).change_task_to_probe(
                                    web_url=new_url, url_hash=user_website.url_hash,
                                    is_tamper_resistant=not task_now_tamper,
                                    new_web_url=new_url, new_url_hash=user_website.url_hash,
                                    new_is_tamper_resistant=task_now_tamper,
                                    version=version.version
                                ))
                                if probe_tasks:
                                    ProbeTaskClient.do_async_probe_tasks(tasks=probe_tasks)

                            return user_website

                    # --- url有更新，是否删除旧监控任务和增加新监控任务----

                    neet_change_version = False
                    # 修改站点地址后，是否还有旧监控网址相同的 监控任务
                    old_url_hash = get_str_hash(old_url)
                    count = MonitorWebsite.objects.filter(url_hash=old_url_hash).count()
                    if count == 0:
                        # 监控任务表移除任务，需要更新任务版本
                        MonitorWebsiteTask.objects.filter(url_hash=old_url_hash, url=old_url).delete()
                        neet_change_version = True
                        # 同步到探测点服务的任务
                        for probe in probes_dict.values():
                            probe_tasks.append(ProbeTaskClient(probe=probe).remove_task_from_probe(
                                web_url=old_url, url_hash=old_url_hash,
                                is_tamper_resistant=False, version=version.version + 1
                            ))
                    else:
                        # 监控任务 防篡改 更新
                        changed, task_now_tamper = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=old_url_hash, full_url=old_url)
                        if changed:
                            neet_change_version = True
                            # 同步到探测点服务的任务
                            for probe in probes_dict.values():
                                probe_tasks.append(ProbeTaskClient(probe=probe).change_task_to_probe(
                                    web_url=old_url, url_hash=old_url_hash,
                                    is_tamper_resistant=not task_now_tamper,
                                    new_web_url=old_url, new_url_hash=old_url_hash,
                                    new_is_tamper_resistant=task_now_tamper,
                                    version=version.version + 1
                                ))

                    # 修改站点地址后，是否需要增加新的监控网址 监控任务
                    new_url_hash = get_str_hash(new_url)
                    count = MonitorWebsiteTask.objects.filter(url_hash=new_url_hash, url=new_url).count()
                    if count == 0:
                        task = MonitorWebsiteTask(url=new_url, is_tamper_resistant=new_tamper_resistant)
                        task.save(force_insert=True)
                        neet_change_version = True
                        # 同步到探测点服务的任务
                        for probe in probes_dict.values():
                            probe_tasks.append(ProbeTaskClient(probe=probe).add_task_to_probe(
                                web_url=new_url, url_hash=new_url_hash,
                                is_tamper_resistant=new_tamper_resistant,
                                version=version.version + 1
                            ))
                    else:
                        # 监控任务 防篡改 更新
                        changed, task_now_tamper = MonitorWebsiteManager._update_task_tamper_resistant(
                            url_hash=new_url_hash, full_url=new_url)
                        if changed:
                            neet_change_version = True
                            # 同步到探测点服务的任务
                            for probe in probes_dict.values():
                                probe_tasks.append(ProbeTaskClient(probe=probe).change_task_to_probe(
                                    web_url=new_url, url_hash=new_url_hash,
                                    is_tamper_resistant=not task_now_tamper,
                                    new_web_url=new_url, new_url_hash=new_url_hash,
                                    new_is_tamper_resistant=task_now_tamper,
                                    version=version.version + 1
                                ))

                    if neet_change_version:
                        version.version_add_1()

                    if probe_tasks:
                        ProbeTaskClient.do_async_probe_tasks(tasks=probe_tasks)
            except Exception as exc:
                raise errors.Error(message=str(exc))
        else:
            try:
                user_website.save(force_update=True)
            except Exception as exc:
                raise errors.Error(message=str(exc))

        return user_website

    @staticmethod
    def get_detection_ponits(enable: bool = None) -> dict:
        """
        查询所有探测点
        """
        _key = MonitorWebsiteManager.CACHE_KEY_DETECTION_POINT
        dict_dps = django_cache.get(_key)
        if dict_dps is None:
            queryset = WebsiteDetectionPoint.objects.select_related('provider').all()
            dict_dps = {point.id: point for point in queryset}
            django_cache.set(_key, dict_dps, 120)

        if enable is None:
            return dict_dps
        elif enable is True:
            return {k: v for k, v in dict_dps.items() if v.enable}

        return {k: v for k, v in dict_dps.items() if not v.enable}

    def get_detection_ponit(self, dp_id: str) -> WebsiteDetectionPoint:
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
            WebsiteQueryChoices.DURATION_SECONDS.value: self.backend.duration_seconds_period,
            WebsiteQueryChoices.SUCCESS.value: self.backend.success_period,
            WebsiteQueryChoices.HTTP_STATUS_STATUS.value: self.backend.http_status_code_period,
            WebsiteQueryChoices.HTTP_DURATION_SECONDS.value: self.backend.http_duration_seconds_period,
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
            WebsiteQueryChoices.SUCCESS.value: self.backend.success_range,
            WebsiteQueryChoices.DURATION_SECONDS.value: self.backend.duration_seconds_range,
            WebsiteQueryChoices.HTTP_STATUS_STATUS.value: self.backend.http_status_code_range,
            WebsiteQueryChoices.HTTP_DURATION_SECONDS.value: self.backend.http_duration_seconds_range
        }[tag]

        return f(**params)

    def query_duration_avg(self, provider: MonitorProvider, start: int, end: int, site_urls: list = None,
                           group: str = 'web'):
        """
        site_urls: 指定要查询的url，当url数量在10以内可以用此参数
        group: in [web, tcp]
        [
            {
                "metric": {
                    "group": "web", # tcp
                    "instance": "thanoswrite.cstcloud.cn:9115",
                    "job": "224e6e4a426968a95ae8c29c81155e1cc2911941",
                    "monitor": "xinxihua",
                    "receive_cluster": "webmonitor",
                    "receive_replica": "0",
                    "tenant_id": "default-tenant",
                    "url": "https://yd.baidu.com/?pcf=2"
                },
                "value": [
                    1690529936.783,
                    "0.400814697"
                ]
            },
        ]
        """
        minutes = math.ceil((end - start) / 60)  # 向上取整
        if minutes <= 0:
            minutes = 1

        if site_urls:
            site_querys = []
            for url in site_urls:
                query = f'avg_over_time(probe_duration_seconds{{group="{group}", url="{url}"}}[{minutes}m])'
                site_querys.append(query)

            query = ' or '.join(site_querys)
        else:
            query = f'avg_over_time(probe_duration_seconds{{group="{group}"}}[{minutes}m])'

        return self.backend.raw_query(
            provider=provider, params={'query': query, 'time': end})

    def query_http_status_code(self, provider: MonitorProvider, timestamp: int, site_urls: list = None):
        """
        site_urls: 指定要查询的url，当url数量在10以内可以用此参数

        [
            {
                "metric": {
                    "job": "224e6e4a426968a95ae8c29c81155e1cc2911941",
                    "url": "https://yd.baidu.com/?pcf=2"
                },
                "value": [1690529936.783, "200"]
            },
        ]
        """
        if site_urls:
            site_querys = []
            for url in site_urls:
                query = f'probe_http_status_code{{group="web",url="{url}"}}'
                site_querys.append(query)

            query = ' or '.join(site_querys)
        else:
            query = f'probe_http_status_code{{group="web"}}'

        return self.backend.raw_query(
            provider=provider, params={'query': query, 'time': timestamp})

    @staticmethod
    def get_site_user_emails(url_hash: str):
        qs = MonitorWebsite.objects.filter(url_hash=url_hash).values(
            'scheme', 'hostname', 'uri', 'user__username', 'odc_id')

        data = {}
        odc_ids = []
        base_valus = None
        for d in qs:
            odc_id = d.pop('odc_id', None)
            if odc_id:
                odc_ids.append(odc_id)
                if not base_valus:
                    base_valus = {'scheme': d['scheme'], 'hostname': d['hostname'], 'uri': d['uri']}

            if not d['user__username']:
                continue

            em = d.pop('user__username', None)
            d['email'] = em
            data[em] = d

        # odc admin
        if odc_ids:
            odc_ids = list(set(odc_ids))
            odc_emails = OrgDataCenterManager.get_odc_admin_emails(odc_ids=odc_ids)
            if not base_valus:
                base_valus = {'scheme': '', 'hostname': '', 'uri': ''}
            for em in odc_emails:
                if em and em not in data:
                    item = base_valus.copy()
                    item['email'] = em
                    data[em] = item

        return list(data.values())
