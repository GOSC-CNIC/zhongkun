import ipaddress
from typing import List, Union

from django.core.cache import cache as dj_cache

from utils.iprestrict import convert_iprange, IPRange
from apps.app_net_manage.models import NetIPAccessWhiteList


class Singleton(type):
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__call__(*args, **kwargs)

        return cls._instance


class NetIPAccessWhiteListManager(Singleton):
    CACHE_KEY = 'cache_net_manage_api_ip_access_whitelist'

    @staticmethod
    def get_whitelist_use_cahce() -> List[str]:
        whitelist = dj_cache.get(NetIPAccessWhiteListManager.CACHE_KEY)
        if whitelist is None:
            whitelist = [i.ip_value for i in NetIPAccessWhiteListManager.get_ip_whitelist_qs()]
            dj_cache.set(NetIPAccessWhiteListManager.CACHE_KEY, whitelist, timeout=60)

        return whitelist

    @staticmethod
    def get_ip_whitelist() -> List[Union[ipaddress.IPv4Network, IPRange]]:
        ip_whitelist = NetIPAccessWhiteListManager.get_whitelist_use_cahce()
        allowed_ips = []
        for ip_rule in ip_whitelist:
            try:
                allowed_ips.append(convert_iprange(ip_rule))
            except Exception:
                pass

        return allowed_ips

    @staticmethod
    def clear_cache():
        dj_cache.delete(NetIPAccessWhiteListManager.CACHE_KEY)

    @staticmethod
    def add_whitelist_obj(ip_value: str, remark: str = ''):
        obj = NetIPAccessWhiteList(ip_value=ip_value, remark=remark)
        obj.save(force_insert=True)
        return obj

    @staticmethod
    def get_ip_whitelist_qs():
        return NetIPAccessWhiteList.objects.all()

    @staticmethod
    def delete_whitelist(ip_values: List[str]):
        return NetIPAccessWhiteList.objects.filter(ip_value__in=ip_values).delete()
