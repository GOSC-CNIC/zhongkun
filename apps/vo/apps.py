from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class VoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.vo'
    verbose_name = _('项目组')
    label = 'vo'
