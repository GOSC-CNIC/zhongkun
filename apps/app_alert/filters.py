import time
import django_filters
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import AlertLifetimeModel
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import utils
from apps.app_alert.utils.enums import AlertStatus


class FiringAlterFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="end", method="status_filter")
    alert_type = django_filters.CharFilter(field_name="type", lookup_expr='exact')
    id = django_filters.CharFilter(field_name="id", method="id_filter")

    def status_filter(self, queryset, field_name, value):
        if value.lower() == AlertStatus.FIRING.value.lower():
            collect = AlertLifetimeModel.objects.filter(end__isnull=True).values("id")
        else:
            collect = AlertLifetimeModel.objects.exclude(end__isnull=True).values("id")
        qs = queryset.filter(id__in=collect)
        return qs

    def id_filter(self, queryset, field_name, value):
        return queryset.filter(id__istartswith=value)

    class Meta:
        model = AlertModel
        fields = {
            "instance": ["exact", ],
            "port": ["exact", ],
            "type": ["exact", ],
            "name": ["exact", ],
            "severity": ["exact", ],
            "cluster": ["exact", ],
            "start": ['lte', 'gte'],
            # "end": ['lte', 'gte'],
        }


class ResolvedAlterFilter(django_filters.FilterSet):
    status = django_filters.CharFilter(field_name="end", method="status_filter")
    alert_type = django_filters.CharFilter(field_name="type", lookup_expr='exact')
    id = django_filters.CharFilter(field_name="id", method="id_filter")

    def status_filter(self, queryset, field_name, value):
        if value.lower() == AlertStatus.FIRING.value.lower():
            collect = AlertLifetimeModel.objects.filter(end__isnull=True).values("id")
        else:
            collect = AlertLifetimeModel.objects.exclude(end__isnull=True).values("id")
        qs = queryset.filter(id__in=collect)
        return qs

    def id_filter(self, queryset, field_name, value):
        return queryset.filter(id__istartswith=value)

    class Meta:
        model = ResolvedAlertModel
        fields = {
            "cluster": ["exact", ],
            "type": ["exact", ],
            "name": ["exact", ],
            "severity": ["exact", ],
            "start": ['lte', 'gte'],
            "end": ['lte', 'gte'],
            "instance": ["exact", ],
            "port": ["exact", ],
        }


class AlertFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filterset = self.get_filterset(request, queryset, view)
        if filterset is None:
            return queryset

        if not filterset.is_valid() and self.raise_exception:
            raise utils.translate_validation(filterset.errors)

        return filterset.qs

    def get_filterset(self, request, queryset, view):
        filterset_class = self.get_filterset_class(view, queryset)
        if filterset_class is None:
            return None
        kwargs = self.get_filterset_kwargs(request, queryset, view)
        return filterset_class(**kwargs)

    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """

        filterset_model_mapping = {filter_class._meta.model: filter_class for filter_class in
                                   getattr(view, "filterset_classes", None)}
        return filterset_model_mapping.get(queryset.model)


class WorkOrderFilter(django_filters.FilterSet):
    alert_id = django_filters.CharFilter(field_name="alert", method="alert_id_filter")

    def alert_id_filter(self, queryset, field_name, value):
        return queryset.filter(alert_id=value)

    class Meta:
        model = AlertWorkOrder
        fields = {
            "id": ["exact", ],
            "collect": ["exact", ],
        }
