from django.contrib import admin
from django.utils.translation import gettext as _
from django.contrib.admin.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'get_change_message')
    search_fields = ('user__username', 'object_id')  # 搜索字段

    @staticmethod
    def get_change_message(obj):
        return obj.get_change_message()


def config_site():
    admin.AdminSite.site_header = _('云联邦后台管理（管理员登录）')
    admin.AdminSite.site_title = _('管理员登录')


config_site()
