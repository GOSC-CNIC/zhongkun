from django.contrib import admin

from utils.model import NoDeleteSelectModelAdmin
from apps.app_global.models import TimedTaskLock


@admin.register(TimedTaskLock)
class TimedTaskLockAdmin(NoDeleteSelectModelAdmin):
    list_display = ['task', 'status', 'start_time', 'end_time', 'host', 'run_desc', 'expire_time', 'notify_time']
    list_display_links = ('task',)

