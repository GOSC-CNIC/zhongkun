import ipaddress
from typing import List, Union, Dict

from django.core.cache import cache as dj_cache
from django.utils.translation import gettext as _

from utils.iprestrict import convert_iprange, IPRange
from apps.app_global.models import GlobalConfig, IPAccessWhiteList


class Singleton(type):
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__call__(*args, **kwargs)

        return cls._instance


class Configs(metaclass=Singleton):
    ConfigName = GlobalConfig.ConfigName
    CACHE_KEY = 'app_global_configs_cache'

    @staticmethod
    def get_configs_no_cache(remove_invalid: bool = False):
        qs = GlobalConfig.objects.all().values('name', 'value')
        configs = {}
        invalid_names = []
        for cfg in qs:
            name = cfg['name']
            if name in GlobalConfig.ConfigName.values:
                configs[cfg['name']] = cfg['value']
            else:
                invalid_names.append(name)

        if remove_invalid and invalid_names:
            GlobalConfig.objects.filter(name__in=invalid_names).delete()

        # 缺少配置
        if len(configs) < len(GlobalConfig.ConfigName.values):
            for name in GlobalConfig.ConfigName.values:
                if name not in configs:
                    obj, created = GlobalConfig.objects.get_or_create(
                        name=name, defaults={'value': GlobalConfig.value_defaults[name]})
                    configs[name] = obj.value

        return configs

    @staticmethod
    def get_configs():
        cache_key = Configs.CACHE_KEY
        configs = dj_cache.get(cache_key)
        if configs:
            return configs

        configs = Configs.get_configs_no_cache(remove_invalid=False)
        dj_cache.set(cache_key, configs, timeout=120)
        return configs

    @staticmethod
    def clear_cache():
        dj_cache.delete(Configs.CACHE_KEY)

    def get(self, name: str):
        """
        查询参数
        """
        if name not in GlobalConfig.ConfigName.values:
            raise Exception(_('未知的全局参数'))

        configs = self.get_configs()
        return configs[name]


class IPAccessWhiteListManager(Singleton):
    ModuleName = IPAccessWhiteList.ModuleName
    CACHE_KEY = 'cache_global_api_ip_access_whitelist'

    @staticmethod
    def get_ip_whitelist_map() -> Dict[str, List[str]]:
        """
        :return:{
            module_name: list[str]
        }
        """
        whitelist_map = {}
        qs = IPAccessWhiteList.objects.filter(
            module_name__in=IPAccessWhiteList.ModuleName.values
        ).values('ip_value', 'module_name')
        for ip_item in qs:
            name = ip_item['module_name']
            if name in whitelist_map:
                whitelist_map[name].append(ip_item['ip_value'])
            else:
                whitelist_map[name] = [ip_item['ip_value']]

        return whitelist_map

    @staticmethod
    def get_whitelist_map_use_cahce() -> Dict[str, List[str]]:
        """
        :return:{
            module_name: list[str]
        }
        """
        whitelist_map = dj_cache.get(IPAccessWhiteListManager.CACHE_KEY)
        if whitelist_map is None:
            whitelist_map = IPAccessWhiteListManager.get_ip_whitelist_map()
            dj_cache.set(IPAccessWhiteListManager.CACHE_KEY, whitelist_map, timeout=60)

        return whitelist_map

    @staticmethod
    def get_module_ip_whitelist(module_name: str) -> List[Union[ipaddress.IPv4Network, IPRange]]:
        ip_whitelist_map = IPAccessWhiteListManager.get_whitelist_map_use_cahce()
        module_whitelist = ip_whitelist_map.get(module_name, [])
        # 所有功能模块白名单
        all_module_whitelist = ip_whitelist_map.get(IPAccessWhiteListManager.ModuleName.ALL_MODULE.value, [])
        if all_module_whitelist:
            module_whitelist += all_module_whitelist

        allowed_ips = []
        for ip_rule in module_whitelist:
            try:
                allowed_ips.append(convert_iprange(ip_rule))
            except Exception:
                pass

        return allowed_ips

    @staticmethod
    def clear_cache():
        dj_cache.delete(IPAccessWhiteListManager.CACHE_KEY)

    @staticmethod
    def add_whitelist_obj(module_name: str, ip_value: str, remark: str = ''):
        if module_name not in IPAccessWhiteList.ModuleName.values:
            raise Exception(_('ip白名单适用功能模块无效'))

        obj = IPAccessWhiteList(
            module_name=module_name, ip_value=ip_value, remark=remark
        )
        obj.save(force_insert=True)
        return obj

    @staticmethod
    def get_ip_whitelist_qs():
        return IPAccessWhiteList.objects.all()

    @staticmethod
    def delete_whitelist(module_name: str, ip_values: List[str]):
        return IPAccessWhiteList.objects.filter(
            module_name=module_name, ip_value__in=ip_values
        ).delete()


global_configs = Configs()
