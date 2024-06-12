import django_filters

from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.permission import PermissionManager
from apps.app_alert.utils.errors import InvalidArgument


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
    exact_menu = django_filters.CharFilter(field_name="menu", method="exact_menu_filter")

    class Meta:
        model = Menu2Chart
        fields = [
            # 'id',
            # 'menu',
            # 'name'
        ]

    def menu_filter(self, queryset, field_name, value):
        """
        查询当前分组和所有下级分组的流量元素对象集合
        """
        perm = PermissionManager(request=self.request)
        target_group = MenuModel.objects.filter(id=value).first()
        if target_group is None:
            raise InvalidArgument(f"invalid menu: `{value}`")
        groups = perm.get_child_nodes(value)  # 当前分组以及所有下级分组
        queryset = queryset.filter(menu__id__in=groups).values_list('id', flat=True)
        for _ in queryset:
            pass
        return queryset

    def exact_menu_filter(self, queryset, field_name, value):
        """
        查询当前组内的流量元素对象
        """
        target_group = MenuModel.objects.filter(id=value).first()
        if target_group is None:
            raise InvalidArgument(f"invalid group: `{value}`")
        return queryset.filter(menu__id=value)


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
