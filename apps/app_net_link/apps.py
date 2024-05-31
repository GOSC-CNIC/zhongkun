from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppNetLinkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_net_link'
    verbose_name = _('链路管理')
    label = 'app_net_link'
