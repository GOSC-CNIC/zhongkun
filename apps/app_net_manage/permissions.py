import ipaddress
from typing import List, Union

from django.core.cache import cache as dj_cache

from utils.iprestrict import IPRestrictor, convert_iprange, IPRange
from apps.app_net_manage.models import NetIPAccessWhiteList
from rest_framework.permissions import BasePermission


class NetIPRestrictor(IPRestrictor):
    CACHE_KEY = 'cache_net_manage_api_ip_access_whitelist'

    @staticmethod
    def get_whitelist_use_cahce() -> List[str]:
        whitelist = dj_cache.get(NetIPRestrictor.CACHE_KEY)
        if whitelist is None:
            whitelist = [i.ip_value for i in NetIPAccessWhiteList.objects.all()]
            dj_cache.set(NetIPRestrictor.CACHE_KEY, whitelist, timeout=60)

        return whitelist

    def get_ip_whitelist_rules(self) -> List[Union[ipaddress.IPv4Network, IPRange]]:
        ip_whitelist = self.get_whitelist_use_cahce()
        allowed_ips = []
        for ip_rule in ip_whitelist:
            try:
                allowed_ips.append(convert_iprange(ip_rule))
            except Exception:
                pass

        return allowed_ips

    def load_ip_rules(self):
        return self.get_ip_whitelist_rules()

    @staticmethod
    def clear_cache():
        dj_cache.delete(NetIPRestrictor.CACHE_KEY)

    @staticmethod
    def add_ip_rule(ip_value: str, remark: str = ''):
        obj = NetIPAccessWhiteList(ip_value=ip_value, remark=remark)
        obj.save(force_insert=True)
        return obj

    @staticmethod
    def delete_ip_rules(ip_values: list):
        return NetIPAccessWhiteList.objects.filter(ip_value__in=ip_values).delete()


class NetIPRestrictPermission(BasePermission):
    def has_permission(self, request, view):
        # try:
        #     LinkIPRestrictor().check_restricted(request=request)
        # except AccessDenied as exc:
        #     self.message = exc.message
        #     return False
        #
        NetIPRestrictor().check_restricted(request=request)
        return True
