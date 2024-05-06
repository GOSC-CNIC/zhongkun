from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppGlobalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_global'
    verbose_name = _('全局配置')
