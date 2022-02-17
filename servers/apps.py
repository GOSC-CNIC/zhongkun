from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'servers'
    verbose_name = _('云主机')
