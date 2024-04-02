from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppNetflowConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_netflow'
    verbose_name = _('网络流量')

