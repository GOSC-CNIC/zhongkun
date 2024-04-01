from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ScanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.app_scan"
    verbose_name = _("漏洞扫描")
    label = "scan"
