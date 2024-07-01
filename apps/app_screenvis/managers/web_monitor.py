from django.utils.translation import gettext_lazy, gettext as _
from django.db import models

from core import errors
from core.web_monitor import WebMonitorTaskClient
from apps.app_screenvis.configs_manager import screen_configs
from apps.app_screenvis.models import ScreenConfig
from apps.app_screenvis.backends.website import WebMonitorQueryAPI, WebsiteExpressionQuery


class WebQueryChoices(models.TextChoices):
    HTTP_STATUS_CODE = 'http_status_code', gettext_lazy('http请求状态码')
    DURATION_SECONDS = 'duration_seconds', gettext_lazy('http请求耗时')
    HTTP_DURATION_SECONDS = 'http_duration_seconds', gettext_lazy('http请求各个部分耗时')


class ScreenWebMonitorManager:
    query_tag_tmpl_map = {
        WebQueryChoices.DURATION_SECONDS.value: WebsiteExpressionQuery.duration_seconds,
        WebQueryChoices.HTTP_DURATION_SECONDS.value: WebsiteExpressionQuery.http_duration_seconds,
        WebQueryChoices.HTTP_STATUS_CODE.value: WebsiteExpressionQuery.http_status_code,
    }

    @staticmethod
    def get_probe_configs():
        return {
            'task_endpoint_url': screen_configs.get(ScreenConfig.ConfigName.PROBE_TASK_ENDPOINT_URL.value),
            'username': screen_configs.get(ScreenConfig.ConfigName.PROBE_TASK_USERNAME.value),
            'password': screen_configs.get(ScreenConfig.ConfigName.PROBE_TASK_PASSWORD.value),
            'query_endpoint_url': screen_configs.get(ScreenConfig.ConfigName.PROBE_QUERY_ENDPOINT_URL.value),
        }

    @staticmethod
    def get_check_task_configs():
        """
        :raises: Error
        """
        cfgs = ScreenWebMonitorManager.get_probe_configs()
        if not cfgs['task_endpoint_url']:
            raise errors.Error(_('站点监控的探针监控任务管理服务地址未配置'))

        if not cfgs['username'] or not cfgs['password']:
            raise errors.Error(_('站点监控的探针监控任务管理服务的身份认证用户名或密码未配置'))

        return cfgs

    @staticmethod
    def build_probe_client():
        cfgs = ScreenWebMonitorManager.get_check_task_configs()
        return WebMonitorTaskClient(
            endpoint_url=cfgs['task_endpoint_url'], username=cfgs['username'], passwd=cfgs['password'])

    @staticmethod
    def add_task_to_probe(web_url: str, url_hash: str, is_tamper_resistant: bool):
        """
        :return:
            OK: None
            Failed: raise Error
        """
        client = ScreenWebMonitorManager.build_probe_client()
        ok, err, res = client.add_task(web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant)
        if not ok:
            raise err

    @staticmethod
    def remove_task_from_probe(web_url: str, url_hash: str, is_tamper_resistant: bool):
        """
        :return:
            OK: None
            Failed: raise Error
        """
        client = ScreenWebMonitorManager.build_probe_client()
        ok, err, res = client.remove_task(web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant)
        if not ok:
            raise err

    @staticmethod
    def change_task_to_probe(
            web_url: str, url_hash: str, is_tamper_resistant: bool,
            new_web_url: str, new_url_hash: str, new_is_tamper_resistant: bool
    ):
        """
        :return:
            OK: None
            Failed: raise Error
        """
        client = ScreenWebMonitorManager.build_probe_client()
        ok, err, res = client.change_task(
            web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant,
            new_web_url=new_web_url, new_url_hash=new_url_hash, new_is_tamper_resistant=new_is_tamper_resistant
        )
        if not ok:
            raise err

    def query(self, tag: str):
        """
        {
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
        cfgs = self.get_probe_configs()
        query_endpoint_url = cfgs['query_endpoint_url']
        if not query_endpoint_url:
            raise errors.Error(message=_('没有配置站点监控数据查询服务地址'))

        tag_tmpl = self.query_tag_tmpl_map[tag]
        querys = {'query': tag_tmpl}
        r = WebMonitorQueryAPI.raw_query(endpoint_url=query_endpoint_url, querys=querys)
        return {tag: r}
