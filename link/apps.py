from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LinkConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'link'
    verbose_name = _('Link科技网链路')
