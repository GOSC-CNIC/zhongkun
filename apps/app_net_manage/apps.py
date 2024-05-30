from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppNetManageConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_net_manage'
    verbose_name = _('综合网管管理')
    label = 'app_net_manage'
