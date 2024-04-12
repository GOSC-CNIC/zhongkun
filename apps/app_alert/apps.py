from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppAlertConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_alert'
    verbose_name = _('告警通知')
