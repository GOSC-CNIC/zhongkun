from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppNetIpamConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_net_ipam'
    verbose_name = _('IP管理')
    label = 'app_net_ipam'
