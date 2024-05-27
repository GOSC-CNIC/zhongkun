from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.servers.handlers.price_handler import DescribePriceHandler
from apps.order.models import Order


class SnapshotPriceViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('云主机快照询价'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description=gettext_lazy('时长')
            ),
            openapi.Parameter(
                name='period_unit',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('时长单位(天、月)'),
                enum=Order.PeriodUnit.values
            ),
            openapi.Parameter(
                name='server_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=True,
                description=gettext_lazy('云主机id')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        云主机快照询价

            http code 200：
            {
              "price": {
                "original": "1277.50",
                "trade": "843.15"
              }
            }
        """
        return DescribePriceHandler().describe_price_snapshot(view=self, request=request)
