from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import TradeGenericViewSet
from api.serializers import trade as trade_serializers
from api.handlers.tradebill_handler import TradeBillHandler
from api.paginations import TradeBillPagination
from bill.models import TransactionBill


class TradeBillViewSet(TradeGenericViewSet):
    """
    交易流水账单视图
    """
    # authentication_classes = []
    permission_classes = [IsAuthenticated]
    pagination_class = TradeBillPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户的交易流水账单'),
        manual_parameters=[
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定VO组的支付记录，需要vo组权限'
            ),
            openapi.Parameter(
                name='trade_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'交易类型, {TransactionBill.TradeType.choices}'
            ),
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付时间段起（含），ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'支付时间段止（不含），ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
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
        列举用户的交易流水账单

            * 通过科技云通行证jwt和session认证

            http code 200：
            {
                "has_next": false,
                "page_size": 100,
                "marker": null,
                "next_marker": null,
                "results": [
                    {
                        "id": "202212050108329956629118",
                        "subject": "subject标题3",
                        "trade_type": "recharge",
                        "trade_id": "ssff",
                        "out_trade_no": "xxx",
                        "trade_amounts": "6.66",
                        "amounts": "6.66",
                        "coupon_amount": "0.00",
                        "after_balance": "6.00",
                        "creation_time": "2022-03-09T01:08:32.988635Z",
                        "remark": "加进去",
                        "owner_id": "5660c8e8-7439-11ed-8287-c8009fe2ebbc",
                        "owner_name": "lilei@cnic.cn",
                        "owner_type": "user",
                        "app_service_id": "app_service2"
                    }
                ]
            }

            http 400, 401, 409:
            {
                "code": "xxx",
                "message": "xxx"
            }
        """
        return TradeBillHandler.list_transaction_bills(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return trade_serializers.TransactionBillSerializer

        return Serializer
