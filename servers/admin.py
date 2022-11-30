from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from utils.model import NoDeleteSelectModelAdmin
from .models import Server, Flavor, ServerArchive


@admin.register(Server)
class ServerAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'azone_id', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'creation_time', 'start_time', 'user', 'task_status', 'center_quota',
                    'pay_type', 'classification', 'vo', 'lock', 'situation', 'situation_time',
                    'default_user', 'show_default_password', 'expiration_time', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['service__data_center', 'service', 'classification']
    raw_id_fields = ('user', )
    list_select_related = ('service', 'user', 'vo')

    @admin.display(
        description=_('默认登录密码')
    )
    def show_default_password(self, obj):
        return obj.raw_default_password

    def has_delete_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(_('不允许从后台删除。'))


@admin.register(ServerArchive)
class ServerArchiveAdmin(NoDeleteSelectModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'service', 'name', 'instance_id', 'vcpus', 'ram', 'disk_size', 'ipv4', 'image',
                    'creation_time', 'user', 'task_status', 'pay_type', 'classification', 'vo',
                    'center_quota',
                    'start_time', 'deleted_time', 'archive_user', 'archive_type', 'remarks')
    search_fields = ['id', 'name', 'image', 'ipv4', 'remarks']
    list_filter = ['service', 'classification']
    raw_id_fields = ('user',)
    list_select_related = ('service', 'user', 'archive_user', 'vo')
    show_full_result_count = False


@admin.register(Flavor)
class FlavorAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'vcpus', 'ram', 'enable', 'service', 'creation_time')
    ordering = ('vcpus', 'ram')
    list_filter = ['service']
