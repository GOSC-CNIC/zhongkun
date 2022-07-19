from django.utils.translation import gettext_lazy
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema

from api.viewsets import PaySignGenericViewSet
from api.paginations import NewPageNumberPagination
from api.serializers import trade as trade_serializers
from api.handlers.trade_handlers import TradeHandler


class TradeViewSet(PaySignGenericViewSet):
    """
    支付交易视图
    """
    permission_classes = []
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('扣费'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=False, url_path='pay', url_name='pay')
    def trade_pay(self, request, *args, **kwargs):
        """
        扣费

            http code 200：
            {
                "id": "202207190608088519002990",
                "subject": "云主机（订购）8个月",
                "payment_method": "balance",    # balance(余额支付)；coupon(代金券支付)；balance+coupon(余额+代金卷)
                "executor": "",
                "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc", # 支付者id
                "payer_name": "lilei@xx.com",       # 支付者名称
                "payer_type": "user",               # user(支付者是用户)；vo(支付者是VO组)
                "amounts": "-1.99",         # 余额扣费金额
                "coupon_amount": "0.00",    # 代金券扣费金额
                "payment_time": "2022-07-19T06:08:08.852251Z",
                "type": "payment",          #
                "remark": "test remark",
                "order_id": "order_id",
                "app_id": "20220719060807",
                "app_service_id": "123"
            }
        """
        return TradeHandler().trade_pay(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'trade_pay':
            return trade_serializers.TradePaySerializer

        return Serializer
