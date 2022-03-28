from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from order.models import ResourceType, Order
from api.paginations import OrderPageNumberPagination
from api.handlers.price_handler import DescribePriceHandler
from api.handlers.order_handler import OrderHandler
from api import serializers


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


class OrderViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = OrderPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举订单'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='resource_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'资源类型, {ResourceType.choices}'
            ),
            openapi.Parameter(
                name='order_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'订单类型，{Order.OrderType.choices}'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付状态，{Order.Status.choices}'
            ),
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'创建时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'创建时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定VO组的订单'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举订单

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "orders": [
                {
                  "id": "2022031006103240183511",
                  "order_type": "new",
                  "status": "cancelled",
                  "total_amount": "0.00",
                  "pay_amount": "0.00",
                  "service_id": "xxx",
                  "service_name": "xxx",
                  "resource_type": "vm",
                  "instance_config": {},
                  "period": 0,
                  "payment_time": "2022-03-10T06:05:00Z",
                  "pay_type": "postpaid",
                  "creation_time": "2022-03-10T06:10:32.478101Z",
                  "user_id": "xxx",
                  "username": "shun",
                  "vo_id": "",
                  "vo_name": "",
                  "owner_type": "user"
                }
              ]
            }
        """
        return OrderHandler().list_order(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('订单详情'),
        request_body=no_body,
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        订单详情

            http code 200：
            {
              "id": "2022031006103240183511",
              "order_type": "new",
              "status": "cancelled",
              "total_amount": "0.00",
              "pay_amount": "0.00",
              "service_id": "",
              "service_name": "",
              "resource_type": "vm",
              "instance_config": {},
              "period": 0,
              "payment_time": "2022-03-10T06:05:00Z",
              "pay_type": "postpaid",
              "creation_time": "2022-03-10T06:10:32.478101Z",
              "user_id": "1",
              "username": "shun",
              "vo_id": "",
              "vo_name": "",
              "owner_type": "user",
              "resources": [
                {
                  "id": "81d9aad0-a03b-11ec-ba16-c8009fe2eb10",
                  "order_id": "2022031006103240183511",
                  "resource_type": "vm",
                  "instance_id": "test",
                  "instance_status": "wait"
                }
              ]
            }
        """
        return OrderHandler().order_detail(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.OrderSerializer
        elif self.action == 'retrieve':
            return serializers.OrderDetailSerializer

        return serializers.serializers.Serializer
