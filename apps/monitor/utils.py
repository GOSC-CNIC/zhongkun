from collections import namedtuple

from django.utils.translation import gettext as _

from core import errors
from apps.service.models import OrgDataCenter
from utils.iprestrict import IPRestrictor, load_allowed_ips


ThanosProvider = namedtuple('ThanosProvider', ['endpoint_url', 'username', 'password'])
LokiProvider = namedtuple('LokiProvider', ['endpoint_url', 'username', 'password'])


def build_thanos_provider(odc: OrgDataCenter) -> ThanosProvider:
    """
    :raises: Error
    """
    if not odc or not odc.thanos_endpoint_url:
        raise errors.ConflictError(message=_('数据中心未配置Thanos服务信息，无法查询监控数据'))

    return ThanosProvider(
        endpoint_url=odc.thanos_endpoint_url,
        username=odc.thanos_username,
        password=odc.thanos_password
    )


def build_loki_provider(odc: OrgDataCenter) -> LokiProvider:
    """
    :raises: Error
    """
    if not odc or not odc.loki_endpoint_url:
        raise errors.ConflictError(message=_('数据中心未配置Loki服务信息，无法查询监控数据'))

    return LokiProvider(
        endpoint_url=odc.loki_endpoint_url,
        username=odc.loki_username,
        password=odc.loki_password
    )


class MonitorEmailAddressIPRestrictor(IPRestrictor):
    SETTING_KEY_NAME = 'API_MONITOR_EMAIL_ALLOWED_IPS'
    _allowed_ip_rules = load_allowed_ips(SETTING_KEY_NAME)

    def reload_ip_rules(self):
        self.allowed_ips = load_allowed_ips(self.SETTING_KEY_NAME)
