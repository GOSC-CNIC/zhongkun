from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = 'apps.app_users'
    verbose_name = _('用户、邮件')
    label = 'users'
