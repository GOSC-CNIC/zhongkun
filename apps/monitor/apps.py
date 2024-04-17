from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.monitor'
    verbose_name = _('监控')
    label = 'monitor'
