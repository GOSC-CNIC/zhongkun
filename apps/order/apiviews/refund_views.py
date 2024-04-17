from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.order import serializers
from apps.order.handlers.refund_handler import RefundOrderHandler
from apps.order.models import OrderRefund


class RefundViewSet(CustomGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
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

            http code 400、403、404、409：
            {
                "code": "xxx",
                "message": "xxx"
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举退订退款记录'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付状态，{OrderRefund.Status.choices}'
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
                description=f'查询指定VO组的退订退款单'
            ),
            openapi.Parameter(
                name='order_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定订单的退订退款单'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举退订退款记录

            http code 200：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "2024030408350766508338",
                        "order": {
                            "id": "2024030408350766120028",
                            "order_type": "new",
                            "status": "unpaid",
                            "total_amount": "333.30",
                            "pay_amount": "0.00",
                            "payable_amount": "333.30",
                            "balance_amount": "0.00",
                            "coupon_amount": "0.00",
                            "service_id": "35wkwm52cb02g1cmgyaeb9h99",
                            "service_name": "test",
                            "resource_type": "vm",
                            "instance_config": {...},
                            "period": 12,
                            "payment_time": null,
                            "pay_type": "prepaid",
                            "creation_time": "2024-03-04T08:35:07.661382Z",
                            "user_id": "35vjjmiunqrmtxgjou3zc9sop",
                            "username": "test",
                            "vo_id": "35w121jbbyhp7y94mh2bup1t9",
                            "vo_name": "test vo",
                            "owner_type": "vo",
                            "cancelled_time": null,
                            "app_service_id": "123",
                            "trading_status": "opening",
                            "number": 3
                        },
                        "order_amount": "123.40",
                        "status": "failed",
                        "status_desc": "",
                        "creation_time": "2024-03-04T08:35:07.661071Z",
                        "update_time": "2024-03-04T08:35:07.661071Z",
                        "resource_type": "vm",
                        "number": 1,
                        "reason": "reason",
                        "refund_amount": "123.40",
                        "balance_amount": "100.00",
                        "coupon_amount": "23.40",
                        "refunded_time": null,
                        "user_id": "35vjjmiunqrmtxgjou3zc9sop",
                        "username": "test",
                        "vo_id": "35w121jbbyhp7y94mh2bup1t9",
                        "vo_name": "test vo",
                        "owner_type": "vo"
                    }
                ]
            }

            * status 退订状态：
                wait: 待退款
                refunded: 已退款
                failed: 退款失败
                cancelled: 取消
        """
        return RefundOrderHandler().list_refund(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除退订退款记录'),
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除退订退款记录

            * 只允许删除 “取消/作废”、“已退款” 状态的退订退款记录；“待退款”、“退款失败”状态的退订记录需要先取消退订后删除；

            http code 204 ok:
            http code 403、404、409：
            {
                "code": "xxx",
                "message": "xxx"
            }
            404: TargetNotExist: 退订退款记录不存在
            403: AccessDenied: 您没有此退订退款记录访问权限
            409: Conflict: 请取消退订退款后再尝试删除
        """
        return RefundOrderHandler.delete_refund(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('取消退订退款'),
        request_body=no_body,
        responses={
            204: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='cancel', url_name='cancel')
    def cancel_refund(self, request, *args, **kwargs):
        """
        取消退订退款

            * 只允许取消 “待退款”、“退款失败”状态的退订记录

            http code 204 ok:
            http code 403、404、409：
            {
                "code": "xxx",
                "message": "xxx"
            }
            404: TargetNotExist: 退订退款记录不存在
            403: AccessDenied: 您没有此退订退款记录访问权限
            409: Conflict: 只允许取消 “待退款”、“退款失败”状态的退订记录
        """
        return RefundOrderHandler.cancel_refund(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.RefundOrderSerializer

        return Serializer
