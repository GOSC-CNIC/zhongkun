from django.contrib import admin
from django.utils.translation import gettext_lazy
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import Menu2Chart
from apps.app_netflow.models import GlobalAdminModel
from apps.app_netflow.models import Menu2Member
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
    filter_horizontal = (
        "charts",
    )


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


@admin.register(GlobalAdminModel)
class GlobalAdministratorAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'member',
        'role',
        'creation',
        'modification',
    ]
    list_display_links = ('id',)
