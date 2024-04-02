import time
import django_filters
from apps.app_netflow.models import MenuCategoryModel
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel


class MenuCategoryFilter(django_filters.FilterSet):
    class Meta:
        model = MenuCategoryModel
        fields = [
            'id',
            'name'
        ]


class ChartFilter(django_filters.FilterSet):
    class Meta:
        model = ChartModel
        fields = [
            # 'id',
            'menu',
            # 'name'
        ]
