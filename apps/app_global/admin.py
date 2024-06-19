from django.contrib import admin, messages

from utils.model import NoDeleteSelectModelAdmin, BaseModelAdmin
from apps.app_global.models import TimedTaskLock, GlobalConfig, IPAccessWhiteList
from apps.app_global.configs_manager import global_configs


@admin.register(TimedTaskLock)
class TimedTaskLockAdmin(NoDeleteSelectModelAdmin):
    list_display = ['task', 'status', 'start_time', 'end_time', 'host', 'run_desc', 'expire_time', 'notify_time']
    list_display_links = ('task',)


@admin.register(GlobalConfig)
class GlobalConfigAdmin(NoDeleteSelectModelAdmin):
    list_display = ['id', 'name', 'value', 'creation_time', 'update_time', 'remark']
    list_display_links = ['id', 'name']

    def save_model(self, request, obj, form, change):
        super().save_model(request=request, obj=obj, form=form, change=change)
        global_configs.clear_cache()

        self.prometheus_config_tips(request=request, obj=obj)

    def prometheus_config_tips(self, request, obj):
        """prometheus 配置提示 """
        from apps.app_probe.handlers.handlers import ProbeHandlers

        content = f'配置内容已保存，'

        try:
            ProbeHandlers().handler_prometheus_config(obj=obj)
        except Exception as e:
            self.message_user(request, content + str(e), level=messages.ERROR)




@admin.register(IPAccessWhiteList)
class IPAccessWhiteListAdmin(BaseModelAdmin):
    list_display = ['id', 'ip_value', 'module_name', 'creation_time', 'update_time', 'remark']
    list_display_links = ['id', 'ip_value']
    list_filter = ('module_name',)
    search_fields = ('ip_value', 'remark')
