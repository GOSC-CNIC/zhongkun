from django.contrib import admin

from utils.model import NoDeleteSelectModelAdmin
from scripts.models import TimedTaskLook


@admin.register(TimedTaskLook)
class TimedTaskLookAdmin(NoDeleteSelectModelAdmin):
    list_display = ['task', 'status', 'start_time', 'end_time', 'host', 'run_desc', 'expire_time', 'notify_time']
    list_display_links = ('task',)
