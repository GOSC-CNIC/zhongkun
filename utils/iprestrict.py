import ipaddress
from collections import namedtuple
from typing import List, Union

from django.conf import settings
from django.utils.translation import gettext as _

from utils import get_remote_ip
from core import errors


IPRange = namedtuple('IPRange', ['start', 'end'])


def load_allowed_ips(setting_key: str) -> List[Union[ipaddress.IPv4Network, IPRange]]:
    ips = getattr(settings, setting_key, [])
    allowed_ips = []
    for ip_str in ips:
        if not isinstance(ip_str, str):
            continue
        if '/' in ip_str:
            try:
                allowed_ips.append(ipaddress.IPv4Network(ip_str, strict=False))
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                pass
        elif '-' in ip_str:
            items = ip_str.split('-')
            if len(items) != 2:
                continue

            start = items[0].strip(' ')
            end = items[1].strip(' ')
            try:
                start = ipaddress.IPv4Address(start)
                end = ipaddress.IPv4Address(end)
                if end >= start:
                    allowed_ips.append(IPRange(start=start, end=end))
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                pass
        else:
            try:
                start = ipaddress.IPv4Address(ip_str)
                allowed_ips.append(IPRange(start=start, end=start))
            except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
                pass

    return allowed_ips


class IPRestrictor:
    _allowed_ip_rules = []

    def reload_ip_rules(self):
        raise NotImplementedError('继承类IPRestrictor的子类没有实现类方法“reload_ip_rules”')

    @property
    def allowed_ips(self):
        return self._allowed_ip_rules

    @allowed_ips.setter
    def allowed_ips(self, ips: list):
        for i in ips:
            if not isinstance(i, IPRange) and not isinstance(i, ipaddress.IPv4Network):
                raise ValueError('IP列表数据项类型必须是“IPv4Network”或者“IPRange”')

        self._allowed_ip_rules = ips

    def check_restricted(self, request):
        client_ip, proxy_ips = get_remote_ip(request)
        self.is_restricted(client_ip=client_ip)

    def is_restricted(self, client_ip: str):
        """
        鉴权客户端ip是否拒绝访问

        :return: False  # 允许访问
        :raises: AccessDenied   # 拒绝访问
        """
        try:
            client_ip = ipaddress.IPv4Address(client_ip)
        except (ipaddress.AddressValueError, ipaddress.NetmaskValueError):
            raise errors.AccessDenied(message=_('无法获取到有效的客户端IPv4地址。') + client_ip)

        for ip_rule in self.allowed_ips:
            if isinstance(ip_rule, IPRange):
                if ip_rule.start <= client_ip <= ip_rule.end:
                    return False
            else:
                if client_ip in ip_rule:
                    return False

        raise errors.AccessDenied(message="此API拒绝从IP地址'%s'访问" % (client_ip,))
