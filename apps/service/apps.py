from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ServiceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.service'
    verbose_name = _('机构、数据中心')
    label = 'service'
