import time
import django_filters
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel


class ChartFilter(django_filters.FilterSet):
    class Meta:
        model = ChartModel
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
