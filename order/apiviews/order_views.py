from django.utils.translation import gettext_lazy, gettext
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import OrderPageNumberPagination, NewPageNumberPagination
from order.handlers.price_handler import DescribePriceHandler
from order import serializers
from order.models import ResourceType, Order, Period
from order.handlers.order_handler import OrderHandler, CASH_COUPON_BALANCE
from servers.serializers import PeriodSerializer
from core import errors


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
                description=gettext_lazy('资源类型') + f', {ResourceType.choices}'
            ),
            openapi.Parameter(
                name='pay_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('付费方式') + '，[prepaid, postpaid]'
            ),
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('时长，单位月，默认(一天)')
            ),
            openapi.Parameter(
                name='flavor_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('云主机配置样式id，资源类型为"vm"时，必须同时指定此参数')
            ),
            openapi.Parameter(
                name='external_ip',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('公网ip')
            ),
            openapi.Parameter(
                name='system_disk_size',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('系统盘大小GiB')
            ),
            openapi.Parameter(
                name='data_disk_size',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('云硬盘大小GiB')
            ),
            openapi.Parameter(
                name='number',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('订购资源数量，默认为1')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        询价

            * resource_type = bucket时，存储询价结果为 GiB*day 价格，订购资源数量number忽略
            * resource_type = vm、disk时，pay_type = postpaid，不指定时长period时（默认一天），询价结果为按量计费每天价格

            http code 200：
            {
              "price": {
                "original": "1277.50",
                "trade": "843.15"
              }
            }
        """
        return DescribePriceHandler().describe_price(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('续费询价'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='resource_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('资源类型') + f', {ResourceType.choices}'
            ),
            openapi.Parameter(
                name='instance_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('查询续费价格的资源实例ID，云主机、云硬盘id')
            ),
            openapi.Parameter(
                name='period',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('时长，单位月')
            ),
            openapi.Parameter(
                name='renew_to_time',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('续费到指定日期，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ，不得与参数“period”同时提交')
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path='renewal', url_name='renewal-price')
    def describe_renewal_price(self, request, *args, **kwargs):
        """
        续费询价

            * 询价的资源实例是按量付费方式时，返回询价时长按量计费的总价格
                询价时长 = period、或者当前时间至renew_to_time时间差

            http code 200：
            {
              "price": {
                "original": "1277.50",
                "trade": "843.15"
              }
            }

            http code 400, 404, 409, ...:
            {
                "code": "MissingResourceType",
                "message": "参数“resource_type”未设置"
            }

            错误码：
            400:
                MissingResourceType: 参数“resource_type”未设置
                InvalidResourceType: 无效的资源类型
                MissingInstanceId: 参数“instance_id”未设置
                InvalidInstanceId: 参数“instance_id”的值无效
                PeriodConflictRenewToTime: 参数“period”和“renew_to_time”不能同时提交
                MissingPeriod: 参数“period”不得为空   # 参数“period”和“renew_to_time”都没有提交时
                InvalidPeriod: 参数“period”的值无效，必须是正整数
                InvalidRenewToTime: 参数“renew_to_time”的值无效的时间格式
            404:
                NotFoundInstanceId: 资源实例不存在
            409:
                InvalidRenewToTime: 参数“renew_to_time”指定的日期不能在资源实例的过期时间之前
        """
        return DescribePriceHandler().describe_renewal_price(view=self, request=request)


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
                  "total_amount": "0.00",   # 原价
                  "pay_amount": "0.00",     # 实付金额
                  "payable_amount": "0.00", # 应付金额
                  "balance_amount": "0.00", # 余额支付金额
                  "coupon_amount": "0.00",  # 券支付金额
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
                  "owner_type": "user",
                  "cancelled_time": "2022-03-10T06:10:32.478101Z",  # 订单作废/取消时间
                  "app_service_id": "xxx"               # service对应的注册于余额结算系统中的APP子服务id
                  "trading_status": "", # 交易状态
                  "number": 3       # 订购资源数量
                }
              ]
            }

            * status 订单状态：
                paid：已支付
                unpaid：未支付
                cancelled：作废
                refunding：退款中
                refund：全额退款
                partrefund：部分退款

            * trading_status 交易状态：
                opening：交易中
                undelivered：订单资源交付失败
                completed：交易成功
                closed：交易关闭
                partdeliver：部分交付失败

            * "instance_config"字段内容说明:
                资源类型为云主机， "resource_type": "vm":
                {
                    "vm_cpu": 8,
                    "vm_ram": 16,            # Gb
                    "vm_systemdisk_size": 50,   # Gb
                    "vm_public_ip": false,
                    "vm_image_id": "24",
                    "vm_network_id": 1,
                    "vm_azone_id": "",
                    "vm_azone_name": ""
                }

                资源类型为云硬盘， "resource_type": "disk":
                {
                    "disk_size": 100,           # Gb
                    "disk_azone_id": "xxx",
                    "disk_azone_name": "xxx"
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
              "total_amount": "0.00",   # 原价
              "pay_amount": "0.00",     # 实付金额
              "payable_amount": "0.00", # 应付金额
              "balance_amount": "0.00", # 余额支付金额
              "coupon_amount": "0.00",  # 券支付金额
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
              "cancelled_time": "2022-03-10T06:10:32.478101Z",  # 订单作废/取消时间
              "app_service_id": "xxx"               # service对应的注册于余额结算系统中的APP子服务id,
              "trading_status": "opening", # 交易状态
              "number": 3,      # 订购资源数量
              "resources": [
                {
                  "id": "81d9aad0-a03b-11ec-ba16-c8009fe2eb10",
                  "order_id": "2022031006103240183511",
                  "resource_type": "vm",
                  "instance_id": "test",
                  "instance_status": "wait",
                  "desc": "xxx",    # 资源交付结果描述
                  "delivered_time": "2022-03-10T06:10:32.478101Z",
                  "instance_delete_time": "2022-03-10T06:10:32.478101Z"     # 不为null时，表示对应资源实例删除时间
                }
              ]
            }
            * status 订单状态：
                paid：已支付
                unpaid：未支付
                cancelled：作废
                refunding：退款中
                refund：全额退款
                partrefund：部分退款

            * trading_status 订单交易状态：
                opening：交易中
                undelivered：订单资源交付失败
                completed：交易成功
                closed：交易关闭
                partdeliver：部分交付失败

            * 资源交付状态 instance_status:
                wait: 待交付
                success: 交付成功
                failed: 交付失败
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
                {Order.PaymentMethod.CASH_COUPON.value}: 只使用资源券, 
                {CASH_COUPON_BALANCE}: 资源券和余额混合支付，优先使用资源券；
                可以通过“coupon_ids”参数指定使用哪些资源券，不指定默认使用所有资源券（过期时间近的优先）。
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
                description=f'指定使用哪些资源券支付；支付方式为资源券时必须指定此参数'
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
                CouponIDsShouldNotExist：仅余额支付方式不能指定资源券
                MissingCouponIDs：仅资源券支付方式必须指定资源券
                InvalidPaymentMethod：支付方式参数“payment_method”值无效
                InvalidCouponIDs：参数“coupon_ids”的值不能为空
                TooManyCouponIDs：最多可以指定使用5个资源券
                DuplicateCouponIDExist：指定的资源券有重复
                InvalidResourceType： 订单订购的资源类型无效
            409：
                CouponBalanceNotEnough：资源券的余额不足
                BalanceNotEnough：余额不足
                CouponNotApplicable：指定的券不能用于此资源的支付
                CouponNoBalance：指定的券没有可用余额
                NoSuchCoupon：资源券不存在
                NotAvailable：资源券无效
                NotEffective：资源券未到生效时间
                ExpiredCoupon：资源券已过期
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除订单'),
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除订单

            http code 204 ok
            http code 400, 403, 404, 409:
            {
                "code": "xx",
                "message": ""
            }
            400: InvalidOrderId: 无效的订单编号
            403: AccessDenied: 您没有此订单访问权限
            404: NotFound: 订单不存在
            409:
                ConflictTradingStatus: 只允许删除交易已关闭、已完成的订单
                OrderUnpaid: 未支付状态的订单，请先取消订单后再尝试删除
                OrderPaid: 已支付状态的订单，资源交付未完成，请先退订退款后再尝试删除
                OrderRefund: 订单正在退款中，请稍后重试
                OrderStatusUnknown: 未知状态的订单
                TryAgainLater: 正在交付订单资源，请稍后重试
        """
        return OrderHandler().delete_order(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.OrderSerializer
        elif self.action == 'retrieve':
            return serializers.OrderDetailSerializer

        return Serializer


class PeriodViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举订购时长选项'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='云主机服务单元ID'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举订购时长选项

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "2023053007251906",
                  "period": 3,
                  "enable": true,
                  "creation_time": "2023-05-30T07:17:55.172308Z",
                  "service_id": "0d084f02-feba-11ed-8442-c8009fe2ebbc"
                }
              ]
            }
        """
        service_id = request.query_params.get('service_id', None)
        if not service_id:
            return self.exception_response(
                exc=errors.InvalidArgument(message=gettext('必须指定服务单元id')))

        qs = Period.objects.filter(Q(service_id=service_id) | Q(service_id__isnull=True)).filter(enable=True).all()
        try:
            periods = self.paginate_queryset(qs)
            serializer = self.get_serializer(instance=periods, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return PeriodSerializer

        return Serializer
