from django.contrib import admin
from django.utils.translation import gettext_lazy
# Register your models here.
from apps.app_netflow.models import MenuCategoryModel
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import RoleModel
from utils.model import BaseModelAdmin


@admin.register(MenuCategoryModel)
class MenuCategoryAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'sort_weight',
        'remark', ]
    list_display_links = (
        'id',
        'name',
        'sort_weight',
        'remark',)


@admin.register(MenuModel)
class MenuAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',
        'category',
        'sort_weight',
        'remark',
    ]
    list_display_links = ('id',)
    filter_horizontal = (
        "chart",
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
        "menus",
        "charts",
        "users",
    )


@admin.register(ChartModel)
class ChartAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'name',

    ]
    list_display_links = ('id',)

