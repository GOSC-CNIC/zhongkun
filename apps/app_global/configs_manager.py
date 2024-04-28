from django.core.cache import cache as dj_cache
from django.utils.translation import gettext as _

from apps.app_global.models import GlobalConfig


class Singleton(type):
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__call__(*args, **kwargs)

        return cls._instance


class Configs(metaclass=Singleton):
    ConfigName = GlobalConfig.ConfigName
    CACHE_KEY = 'app_global_configs_cache'

    @staticmethod
    def get_configs():
        cache_key = Configs.CACHE_KEY
        configs = dj_cache.get(cache_key)
        if configs:
            return configs

        qs = GlobalConfig.objects.all().values('name', 'value')
        configs = {}
        invalid_names = []
        for cfg in qs:
            name = cfg['name']
            if name in GlobalConfig.ConfigName.values:
                configs[cfg['name']] = cfg['value']
            else:
                invalid_names.append(name)

        if invalid_names:
            GlobalConfig.objects.filter(name__in=invalid_names).delete()

        # 缺少配置
        if len(configs) < len(GlobalConfig.ConfigName.values):
            for name in GlobalConfig.ConfigName.values:
                if name not in configs:
                    obj, created = GlobalConfig.objects.get_or_create(
                        name=name, defaults={'value': GlobalConfig.value_defaults[name]})
                    configs[name] = obj.value

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


global_configs = Configs()
