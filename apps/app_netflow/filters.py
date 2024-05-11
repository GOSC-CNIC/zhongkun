import django_filters

from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import Menu2Chart
from apps.app_netflow.models import Menu2Member
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import GlobalAdminModel


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
    class Meta:
        model = Menu2Chart
        fields = [
            # 'id',
            'menu',
            # 'name'
        ]


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
