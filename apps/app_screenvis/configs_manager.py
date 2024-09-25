from django.core.cache import cache as dj_cache
from django.utils.translation import gettext as _

from apps.app_screenvis.models import ScreenConfig


class Singleton(type):
    def __call__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = super().__call__(*args, **kwargs)

        return cls._instance


class Configs(metaclass=Singleton):
    ConfigName = ScreenConfig.ConfigName
    CACHE_KEY = 'app_screenvis_configs_cache'

    @staticmethod
    def get_configs_no_cache(remove_invalid: bool = False):
        qs = ScreenConfig.objects.all().values('name', 'value')
        configs = {}
        invalid_names = []
        for cfg in qs:
            name = cfg['name']
            if name in ScreenConfig.ConfigName.values:
                configs[cfg['name']] = cfg['value']
            else:
                invalid_names.append(name)

        if remove_invalid and invalid_names:
            ScreenConfig.objects.filter(name__in=invalid_names).delete()

        # 缺少配置
        if len(configs) < len(ScreenConfig.ConfigName.values):
            for name in ScreenConfig.ConfigName.values:
                if name not in configs:
                    obj, created = ScreenConfig.objects.get_or_create(
                        name=name, defaults={'value': ScreenConfig.value_defaults.get(name, '')})
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
        if name not in ScreenConfig.ConfigName.values:
            raise Exception(_('未知的配置参数'))

        configs = self.get_configs()
        return configs[name]

    def add_or_update(self, name: str, value):
        if name not in ScreenConfig.ConfigName.values:
            raise Exception(_('未知的配置参数'))

        cfg = ScreenConfig.objects.filter(name=name).first()
        if cfg is None:
            cfg = ScreenConfig(name=name, value=value)
        else:
            cfg.value = value

        cfg.clean()
        cfg.save()
        self.clear_cache()


screen_configs = Configs()
