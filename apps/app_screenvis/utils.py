from collections import namedtuple

from django.utils.translation import gettext as _

from core import errors
from core.loggers import config_script_logger
from apps.app_screenvis.configs_manager import screen_configs


screen_logger = config_script_logger(name='screenvis-logger', filename='screenvis.log')

MetricProvider = namedtuple('MetricProvider', ['endpoint_url', 'username', 'password'])
LokiProvider = namedtuple('LokiProvider', ['endpoint_url', 'username', 'password'])


def build_metric_provider() -> MetricProvider:
    """
    :raises: Error
    """
    metric_endpoint_url = screen_configs.get(screen_configs.ConfigName.METRIC_QUERY_ENDPOINT_URL.value)
    if not metric_endpoint_url:
        raise errors.ConflictError(message=_('未配置指标数据查询服务地址信息，无法查询监控数据'))

    if not metric_endpoint_url.startswith('http'):
        raise errors.ConflictError(message=_('配置指标数据查询服务地址格式无效，无法查询监控数据'))

    return MetricProvider(
        endpoint_url=metric_endpoint_url,
        username='', password=''
    )
