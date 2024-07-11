import django_filters
from apps.app_alert.models import AlertModel
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_alert.utils.enums import AlertStatus


class AlterFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name="id", method="id_filter")
    status = django_filters.CharFilter(field_name="end", method="status_filter")
    alert_type = django_filters.CharFilter(field_name="type", lookup_expr='exact')
    has_ticket = django_filters.CharFilter(field_name="ticket", method="has_ticket_filter")

    def status_filter(self, queryset, field_name, value):
        if value.lower() == AlertStatus.FIRING.value:
            queryset = queryset.filter(status=AlertStatus.FIRING.value)
            return queryset
        elif value.lower() == AlertStatus.RESOLVED.value:
            queryset = queryset.filter(status=AlertStatus.RESOLVED.value)
            return queryset

    def has_ticket_filter(self, queryset, field_name, value):
        if value == 'true':
            queryset = queryset.filter(ticket__isnull=False)
        elif value == 'false':
            queryset = queryset.filter(ticket__isnull=True)
        return queryset

    def id_filter(self, queryset, field_name, value):
        return queryset.filter(id__istartswith=value)

    class Meta:
        model = AlertModel
        fields = {
            "fingerprint": ['exact'],
            "instance": ["exact", ],
            "port": ["exact", ],
            "type": ["exact", ],
            "name": ["exact", ],
            "severity": ["exact", ],
            "cluster": ["exact", ],
            "start": ['lte', 'gte'],
        }


class AlertFilterBackend(DjangoFilterBackend):
    def get_filterset_class(self, view, queryset=None):
        """
        Return the `FilterSet` class used to filter the queryset.
        """
        return AlterFilter





