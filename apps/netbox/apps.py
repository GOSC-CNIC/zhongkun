from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class NetboxConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'netbox'
    verbose_name = _('IP和链路管理')
