from django.contrib import admin
from django.utils.translation import gettext_lazy
# Register your models here.
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import RoleModel
from utils.model import BaseModelAdmin


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

@admin.register(RoleModel)
class MenuAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'sort_weight',
        'remark',
    ]
    list_display_links = ('id',)
    filter_horizontal = (
        "charts",
        "users",
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

