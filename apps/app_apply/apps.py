from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ApplyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_apply'
    verbose_name = _('申请审批')
    label = 'apply'  # app_label
