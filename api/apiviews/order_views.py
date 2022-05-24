from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from order.models import ResourceType, Order
from api.paginations import OrderPageNumberPagination
from api.handlers.price_handler import DescribePriceHandler
from api.handlers.order_handler import OrderHandler, CASH_COUPON_BALANCE
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('支付订单'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='payment_method',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"""支付方式，
                {Order.PaymentMethod.BALANCE.value}: 只使用账户余额, 
                {Order.PaymentMethod.CASH_COUPON.value}: 只使用代金券, 
                {CASH_COUPON_BALANCE}: 代金券和余额混合支付，优先使用代金券；
                可以通过“coupon_ids”参数指定使用哪些代金券，不指定默认使用所有代金券（过期时间近的优先）。
                """
            ),
            openapi.Parameter(
                name='coupon_ids',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(
                    type=openapi.TYPE_STRING
                ),
                collectionFormat='multi',
                maxLength=5,
                required=False,
                description=f'指定使用哪些代金券支付；支付方式为代金券时必须指定此参数'
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='pay', url_name='pay-order')
    def pay_order(self, request, *args, **kwargs):
        """
        支付订单

            http code 200：
            {
                "order_id": "xxx"
            }

            * 可能的错误码：
            400：
                InvalidOrderId：无效的订单编号
                MissingPaymentMethod：支付方式参数“payment_method”
                CouponIDsShouldNotExist：仅余额支付方式不能指定代金券
                MissingCouponIDs：仅代金券支付方式必须指定代金券
                InvalidPaymentMethod：支付方式参数“payment_method”值无效
                InvalidCouponIDs：参数“coupon_ids”的值不能为空
                TooManyCouponIDs：最多可以指定使用5个代金券
                DuplicateCouponIDExist：指定的代金券有重复
                InvalidResourceType： 订单订购的资源类型无效
            409：
                CouponBalanceNotEnough：代金券的余额不足
                BalanceNotEnough：余额不足
                CouponNotApplicable：指定的券不能用于此资源的支付
                CouponNoBalance：指定的券没有可用余额
                NoSuchCoupon：代金券不存在
                NotAvailable：代金券无效
                NotEffective：代金券未到生效时间
                ExpiredCoupon：代金券已过期
        """
        return OrderHandler().pay_order(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('订单资源交付失败, 索要订单资源，主动触发交付订单资源'),
        request_body=no_body,
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='claim', url_name='claim-order')
    def claim_order(self, request, *args, **kwargs):
        """
        订单资源交付失败, 索要订单资源，主动触发再一次尝试交付订单资源

            http code 200：
            {
                "order_id": "xxx"
            }
        """
        return OrderHandler().claim_order_resource(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('取消订单'),
        request_body=no_body,
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='cancel', url_name='cancel-order')
    def cancel_order(self, request, *args, **kwargs):
        """
        取消订单

            http code 200：
            {
                "order_id": "xxx"
            }
        """
        return OrderHandler().cancel_order(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.OrderSerializer
        elif self.action == 'retrieve':
            return serializers.OrderDetailSerializer

        return serializers.serializers.Serializer
