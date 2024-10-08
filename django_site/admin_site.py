from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.models import LogEntry, ContentType
from django.conf import settings

from core import site_configs_manager as site_configs


site_header_lazy = site_configs.get_website_brand_lazy(default='ZhongKun')
ADMIN_SORTED_APP_LIST = settings.ADMIN_SORTED_APP_LIST


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'get_change_message')
    search_fields = ('user__username', 'object_id')  # 搜索字段

    @staticmethod
    def get_change_message(obj):
        return obj.get_change_message()


class ContentTypeAdmin(admin.ModelAdmin):
    pass


def get_app_list(self, request, app_label=None):
    """
    Return a sorted list of all the installed apps that have been
    registered in this site.
    """
    app_dict = self._build_app_dict(request, app_label)
    # admin not display baton's model
    if 'baton' in app_dict:
        app_dict.pop('baton', None)

    # Sort the apps alphabetically.
    # app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())

    # 如果应用标签(如app1, app2, 在ADMIN_SORTED_APP_LIST中，则按其索引排， 否则排最后面
    app_count = len(ADMIN_SORTED_APP_LIST)  # 获取app数量
    app_list = sorted(
        app_dict.values(),
        key=lambda x: ADMIN_SORTED_APP_LIST.index(
            x['app_label']) if x['app_label'] in ADMIN_SORTED_APP_LIST else app_count
    )

    # Sort the models alphabetically within each app.
    for app in app_list:
        app["models"].sort(key=lambda x: x["name"])

    return app_list


def config_site():
    admin.AdminSite.site_header = site_header_lazy
    admin.AdminSite.site_title = _('管理员登录')
    admin.AdminSite.get_app_list = get_app_list  # 覆盖原有的get_app_list方法
    admin.site.site_header = admin.AdminSite.site_header
    admin.site.site_title = admin.AdminSite.site_title

    admin.site.register(LogEntry, admin_class=LogEntryAdmin)
    admin.site.register(ContentType, admin_class=ContentTypeAdmin)


config_site()
