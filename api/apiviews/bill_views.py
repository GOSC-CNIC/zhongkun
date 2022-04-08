from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import PaymentHistoryPagination
from api.handlers.bill_handler import PaymentHistoryHandler
from api import serializers
from order.models import ResourceType
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
                description=f'查询指定VO组的支付记录，需要vo组权限, 或管理员权限，不能与user_id同时使用'
            ),
            openapi.Parameter(
                name='payment_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付记录类型, {PaymentHistory.Type.choices}'
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
                name='resource_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'产品类型, {ResourceType.choices}'
            ),
            openapi.Parameter(
              name='service_id',
              in_=openapi.IN_QUERY,
              type=openapi.TYPE_STRING,
              required=False,
              description=f'服务id, 以管理员身份请求时需要有管理权限'
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定用户的支付记录，仅以管理员身份查询时使用'
            ),
        ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
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
                  "id": "9f30d8d0-b713-11ec-bb91-c8009fe2eb10",
                  "payment_method": "balance",
                  "executor": "metering",
                  "payer_id": "1",
                  "payer_name": "shun",
                  "payer_type": "user",     # user or vo
                  "amounts": "-2.68",
                  "before_payment": "-197.49",
                  "after_payment": "-200.17",
                  "payment_time": "2022-04-07T07:59:23.598408Z",
                  "type": "payment",
                  "remark": "按量计费",
                  "order_id": "",
                  "resource_type": "vm",
                  "service_id": "1ff0a8a0-490b-11ec-8e98-c8009fe2eb10",
                  "instance_id": "d1d10b24-4c25-11ec-a2dc-c8009fe2eb10"
                }
              ]
            }
        """
        return PaymentHistoryHandler().list_payment_history(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.PaymentHistorySerializer

        return serializers.serializers.Serializer
