import time
import django_filters
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ServiceAdminUser
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import TicketResolutionCategory
from apps.app_alert.models import TicketResolution
from apps.app_alert.models import AlertTicket
from apps.app_alert.models import TicketHandler
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_alert.utils.enums import AlertStatus


class AlterFilter(django_filters.FilterSet):
    id = django_filters.CharFilter(field_name="id", method="id_filter")
    status = django_filters.CharFilter(field_name="end", method="status_filter")
    alert_type = django_filters.CharFilter(field_name="type", lookup_expr='exact')

    def status_filter(self, queryset, field_name, value):
        if value.lower() == AlertStatus.FIRING.value:
            queryset = queryset.filter(status=AlertStatus.FIRING.value)
            return queryset
        elif value.lower() == AlertStatus.RESOLVED.value:
            queryset = queryset.filter(status=AlertStatus.RESOLVED.value)
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


class WorkOrderFilter(django_filters.FilterSet):
    alert_id = django_filters.CharFilter(field_name="alert", method="alert_id_filter")

    def alert_id_filter(self, queryset, field_name, value):
        return queryset.filter(alert_id=value)

    class Meta:
        model = AlertWorkOrder
        fields = {
            "id": ["exact", ],
        }


class TicketResolutionCategoryFilter(django_filters.FilterSet):
    class Meta:
        model = TicketResolutionCategory
        fields = {
            "service": ["exact", ],
        }


class TicketResolutionFilter(django_filters.FilterSet):
    class Meta:
        model = TicketResolution
        fields = {
            "id": ["exact", ],
        }


class TicketHandlerFilter(django_filters.FilterSet):
    class Meta:
        model = TicketHandler
        fields = {
            "id": ["exact", ],
        }


class AlertTicketFilter(django_filters.FilterSet):
    category_id = django_filters.CharFilter(field_name="resolution", method="category_id_filter")
    resolution_id = django_filters.CharFilter(field_name="resolution", method="resolution_id_filter")

    class Meta:
        model = AlertTicket
        fields = {
            "id": ["exact", ],
            # "service": ["exact", ],
            "severity": ["exact", ],
            "status": ["exact", ],
        }

    def category_id_filter(self, queryset, field_name, value):
        return queryset.filter(resolution__category__id=value)

    def resolution_id_filter(self, queryset, field_name, value):
        return queryset.filter(resolution__id=value)


class ServiceAdminUserFilter(django_filters.FilterSet):
    service = django_filters.CharFilter(field_name="service", method="service_filter")

    class Meta:
        model = ServiceAdminUser
        fields = {

        }

    def service_filter(self, queryset, field_name, value):
        from apps.app_alert.models import AlertService
        service = AlertService.objects.filter(name_en=value).first()
        return queryset.filter(service=service)
