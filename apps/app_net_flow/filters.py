import django_filters

from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.permission import PermissionManager


class ChartFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    instance_name = django_filters.CharFilter(lookup_expr='icontains')
    if_alias = django_filters.CharFilter(lookup_expr='icontains')
    if_address = django_filters.CharFilter(lookup_expr='icontains')
    device_ip = django_filters.CharFilter(lookup_expr='icontains')
    port_name = django_filters.CharFilter(lookup_expr='icontains')
    class_uuid = django_filters.CharFilter(lookup_expr='icontains')
    remark = django_filters.CharFilter(lookup_expr='icontains')
    group = django_filters.CharFilter(field_name="id", method="group_filter")

    class Meta:
        model = ChartModel
        fields = []

    def group_filter(self, queryset, field_name, value):
        menu = MenuModel.objects.filter(id=value).first()
        if menu:
            queryset = queryset.exclude(id__in=menu.charts.values_list('id', flat=True))
        return queryset


class Menu2ChartFilter(django_filters.FilterSet):
    menu = django_filters.CharFilter(field_name="menu", method="menu_filter")

    class Meta:
        model = Menu2Chart
        fields = [
            # 'id',
            # 'menu',
            # 'name'
        ]

    def menu_filter(self, queryset, field_name, value):
        """
        超级管理员和运维管理员:
            显示当前分组和所有下级分组

        组员和组管理员:
            显示当前分组和有权限的下级分组
        """
        perm = PermissionManager(request=self.request)
        target_group = MenuModel.objects.filter(id=value).first()
        groups = perm.get_all_children_groups(target_group)
        menu_id_list = list()
        items = list()
        for g in groups:
            for obj in queryset.filter(menu=g):
                if obj.chart.id not in menu_id_list:
                    menu_id_list.append(obj.chart.id)
                    items.append(obj.id)
        return queryset.filter(id__in=items)


class GlobalAdminFilter(django_filters.FilterSet):
    class Meta:
        model = GlobalAdminModel
        fields = [
            'role',
        ]


class Menu2MemberFilter(django_filters.FilterSet):
    class Meta:
        model = Menu2Member
        fields = [
            # 'id',
            'menu',
            # 'name'
        ]


class MenuFilter(django_filters.FilterSet):
    class Meta:
        model = MenuModel
        fields = [
            'id',
            # 'menu',
            # 'name'
        ]
