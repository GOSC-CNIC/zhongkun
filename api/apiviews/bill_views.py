from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import PaymentHistoryPagination
from api.handlers.bill_handler import PaymentHistoryHandler
from api.serializers import serializers
from bill.models import PaymentHistory


class PaymentHistoryViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = PaymentHistoryPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举支付记录'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定VO组的支付记录，需要vo组权限'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付状态, {PaymentHistory.Status.choices}'
            ),
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
              name='app_service_id',
              in_=openapi.IN_QUERY,
              type=openapi.TYPE_STRING,
              required=False,
              description=f'app服务id'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举支付记录

            http code 200：
            {
              "has_next": true,
              "page_size": 2,
              "marker": "cD0yMDIyLTA0LTA3KzA3JTNBNTklM0EyMy42MTc4MjYlMkIwMCUzQTAw",
              "next_marker": "cD0yMDIyLTA0LTA3KzA3JTNBNTklM0EyMy41NzY5NjElMkIwMCUzQTAw",
              "results": [
                {
                  "id": "xxxx",
                  "subject": "云主机（订购）8个月",
                  "payment_method": "balance",
                  "executor": "metering",
                  "payer_id": "1",
                  "payer_name": "shun",
                  "payer_type": "user",     # user or vo
                  "payable_amounts": "160.00",    # 应付金额
                  "amounts": "-60.00",           # 余额支付金额
                  "coupon_amount": "-100.00",   # 资源券支付金额
                  "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                  "payment_time": "2022-04-07T07:59:23.598408Z",        # 支付完成时间，未支付成功时为空
                  "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                  "status_desc": "",    # 状态描述
                  "remark": "按量计费",
                  "order_id": "xxx",
                  "app_service_id": "sxxxx",
                  "app_id": "xxxx"
                }
              ]
            }
        """
        return PaymentHistoryHandler().list_payment_history(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('支付记录详细信息'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        支付记录详细信息

            http code 200：
            {
              "id": "202207040607159512716434",
              "subject": "云服务器按量计费",
              "payment_method": "coupon",
              "executor": "metering",
              "payer_id": "1",
              "payer_name": "shun",
              "payer_type": "user",
              "payable_amounts": "160.00",    # 应付金额
              "amounts": "-60.00",           # 余额支付金额
              "coupon_amount": "-100.00",   # 资源券支付金额
              "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
              "payment_time": "2022-04-07T07:59:23.598408Z",        # 支付完成时间，未支付成功时为空
              "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
              "status_desc": "",    # 状态描述
              "remark": "server id=0e475786-9ac1-11ec-857b-c8009fe2eb10, 2022-07-03",
              "order_id": "s-8aa93412fb5f11ec8ac1c8009fe2ebbc",
              "app_id": "xxx",
              "app_service_id": "s20220623023119",
              "coupon_historys": [
                {
                  "cash_coupon_id": "144765530930",
                  "amounts": "-15.97",
                  "before_payment": "1000.00",
                  "after_payment": "984.03",
                  "creation_time": "2022-07-04T06:07:15.955151Z"
                }
              ]
            }
        """
        return PaymentHistoryHandler().detail_payment_history(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.PaymentHistorySerializer

        return Serializer
