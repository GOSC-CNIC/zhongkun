from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApplyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scripts'
    verbose_name = _('定时任务')
    label = 'scripts'  # app_label
