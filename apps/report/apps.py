from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.report'
    verbose_name = _('报表')
    label = 'report'
