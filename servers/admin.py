from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Server, Flavor, ServerArchive


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'instance_id', 'vcpus', 'ram', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'center_quota', 'user_quota',
                    'default_user', 'show_default_password', 'expiration_time', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service__data_center', 'service']
    raw_id_fields = ('user', 'user_quota')
    list_select_related = ('service', 'user', 'user_quota')

    @admin.display(
        description=_('默认登录密码')
    )
    def show_default_password(self, obj):
        return obj.raw_default_password


@admin.register(ServerArchive)
class ServerArchiveAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'vcpus', 'ram', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'center_quota', 'user_quota',
                    'deleted_time', 'archive_user', 'remarks')
    search_fields = ['name', 'image', 'ipv4', 'remarks']
    list_filter = ['service']
    raw_id_fields = ('user',)
    list_select_related = ('service', 'user', 'user_quota', 'archive_user')
    show_full_result_count = False


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'creation_time')
