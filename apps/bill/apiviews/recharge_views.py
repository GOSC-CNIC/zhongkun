from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema

from bill.apiviews import TradeGenericViewSet
from bill import trade_serializers
from bill.handlers.recharge_handler import RechargeHandler


class RechargeViewSet(TradeGenericViewSet):
    """
    充值视图
    """
    # authentication_classes = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('人工充值'),
        manual_parameters=[],
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=False, url_path='manual', url_name='manual')
    def manual_recharge(self, request, *args, **kwargs):
        """
        人工充值

            * 通过科技云通行证jwt和session认证

            http code 200：
            {
                "recharge_id": "202212050108329956629118",
            }

            http 400, 401, 409:
            {
                "code": "xxx",
                "message": "xxx"
            }
        """
        return RechargeHandler.manual_recharge(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'manual_recharge':
            return trade_serializers.RechargeManualSerializer

        return Serializer
