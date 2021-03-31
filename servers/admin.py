from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Server, Flavor, ServerArchive


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'instance_id', 'vcpus', 'ram', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'center_quota', 'user_quota', 'due_time', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service__data_center', 'service']
    raw_id_fields = ('user', 'user_quota')
    list_select_related = ('service', 'user', 'user_quota')

    def due_time(self, obj):
        q = obj.user_quota
        if not q:
            return None

        if not q.due_time:
            return "无"

        return q.due_time

    due_time.short_description = _('过期时间')


@admin.register(ServerArchive)
class ServerArchiveAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'vcpus', 'ram', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'center_quota', 'user_quota', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service']
    raw_id_fields = ('user',)
    list_select_related = ('service', 'user', 'user_quota')
    show_full_result_count = False


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'creation_time')
