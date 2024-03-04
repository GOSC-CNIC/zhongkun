from django.utils.translation import gettext_lazy, gettext
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import OrderPageNumberPagination
from order import serializers
from order.handlers.refund_handler import RefundOrderHandler


class RefundViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = OrderPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交订单退订退款申请'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='order_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('退订订单编号')
            ),
            openapi.Parameter(
                name='reason',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('退订原因')
            )
        ],
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交订单退订退款申请

            * 可退订的订单状态：已支付状态的订单，资源未交付、交付失败、订购多个资源有部分资源交付失败
            * 预付费订单，资源交付失败，全额退款；如果订购多个资源，资源交付部分成功，退订只退还未交付资源所占的金额
            * 按量付费订单，退订不涉及退款，退订后会关闭订单；如果订购多个资源，资源交付部分成功，退订后会关闭订单，已交付资源不会退订

            http code 200：
            {
                "refund_id": "xxx"
            }

            * 可能的错误码：
            400：
                InvalidArgument：无效的订单编号/退订原因不能超过255个字符
            404:
                NotFound: 订单编号不存在
                TargetNotExist: 退订退款单不存在/
            403：
                AccessDenied: 无订单访问权限
            409：
                OrderTradingClosed: 订单交易已关闭
                OrderTradingCompleted: 订单交易已完成
                OrderUnpaid: 订单未支付
                OrderCancelled: 订单已作废
                OrderRefund: 订单已退款
                OrderRefund: 订单正在退款中
                OrderStatusUnknown: 未知状态的订单
                OrderDelivering: 订单资源正在交付中
                OrderActionUnknown: 订单处在未知的操作动作中，请稍后重试，或者联系客服人员人工处理
                Conflict: xxx
        """
        return RefundOrderHandler().create_refund(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return Serializer
