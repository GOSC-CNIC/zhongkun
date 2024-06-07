from django.contrib import admin
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.models import Menu2Member
from utils.model import BaseModelAdmin


# Register your models here.

@admin.register(MenuModel)
class MenuAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'level',
        'father',
        'sort_weight',
        'remark',
    ]
    list_display_links = ('id',)

    search_fields = ('id', 'name')  # 搜索字段


@admin.register(ChartModel)
class ChartAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'instance_name',
        'if_alias',
        'if_address',
        'device_ip',
        'port_name',
        'class_uuid',
        'band_width',
        'sort_weight',

    ]
    list_display_links = ('id',)
    search_fields = ('id', 'instance_name', 'if_alias', 'device_ip', 'port_name')  # 搜索字段


@admin.register(Menu2Chart)
class Menu2ChartAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'menu',
        'chart',
        'title',
        'sort_weight',

    ]
    list_display_links = ('id',)
    raw_id_fields = ('menu', 'chart')
    search_fields = (
        'id', 'menu__name', 'menu__id', 'chart__id',
        'chart__instance_name', 'chart__device_ip', 'title'
    )  # 搜索字段


@admin.register(Menu2Member)
class Menu2MemberAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'menu',
        'member',
        'role',
        'inviter',

    ]
    list_display_links = ('id',)
    raw_id_fields = ('menu', 'member')
    search_fields = ('id', 'menu__id', 'menu__name', 'member__email', 'member__username', 'title')  # 搜索字段

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.inviter = request.user.username
        obj.save()


@admin.register(GlobalAdminModel)
class GlobalAdministratorAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'member',
        'role',
        'inviter',
        'creation',
    ]
    list_display_links = ('id',)
    raw_id_fields = ('member',)
    search_fields = ('id', 'member__email', 'member__username', 'role',)  # 搜索字段

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.inviter = request.user.username
        obj.save()
