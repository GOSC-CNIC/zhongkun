from collections import namedtuple

from django.utils.translation import gettext as _

from core import errors
from apps.app_screenvis.models import DataCenter


MetricProvider = namedtuple('MetricProvider', ['endpoint_url', 'username', 'password'])
LokiProvider = namedtuple('LokiProvider', ['endpoint_url', 'username', 'password'])


def build_metric_provider(odc: DataCenter) -> MetricProvider:
    """
    :raises: Error
    """
    if not odc or not odc.metric_endpoint_url:
        raise errors.ConflictError(message=_('数据中心未配置Metric服务信息，无法查询监控数据'))

    return MetricProvider(
        endpoint_url=odc.metric_endpoint_url,
        username='', password=''
    )


def build_loki_provider(odc: DataCenter) -> LokiProvider:
    """
    :raises: Error
    """
    if not odc or not odc.loki_endpoint_url:
        raise errors.ConflictError(message=_('数据中心未配置Loki服务信息，无法查询监控数据'))

    return LokiProvider(
        endpoint_url=odc.loki_endpoint_url,
        username='', password=''
    )
