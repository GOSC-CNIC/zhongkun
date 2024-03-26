from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ScreenvisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_screenvis'
    verbose_name = _('大屏展示')
    label = 'app_screenvis'     # app_label
