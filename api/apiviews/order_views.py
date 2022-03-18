from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from order.models import ResourceType
from api.handlers.price_handler import DescribePriceHandler


class PriceViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('询价'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='resource_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'资源类型, {ResourceType.choices}'
            ),
            openapi.Parameter(
                name='pay_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='付费方式，[prepaid, postpaid]'
            ),
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description='时长，单位月，默认(一天)'
            ),
            openapi.Parameter(
                name='flavor_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'云主机配置样式id，资源类型为{ResourceType.VM}时，必须同时指定此参数'
            ),
            openapi.Parameter(
                name='external_ip',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='公网ip'
            ),
            openapi.Parameter(
                name='system_disk_size',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description='系统盘大小GiB'
            ),
            openapi.Parameter(
                name='data_disk_size',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description='云硬盘大小GiB'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        询价

            http code 200：
            {
              "price": {
                "original": "1277.5000",
                "trade": "843.1500"
              }
            }
        """
        return DescribePriceHandler().describe_price(view=self, request=request)
