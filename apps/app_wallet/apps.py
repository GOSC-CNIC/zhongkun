from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BillConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.app_wallet'
    verbose_name = _('余额、账单、券')
    label = 'bill'
