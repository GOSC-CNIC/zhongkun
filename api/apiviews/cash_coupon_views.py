from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import DefaultPageNumberPagination
from api.handlers.cash_coupon_handler import CashCouponHandler


class CashCouponViewSet(CustomGenericViewSet):
    """
    代金券视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('领取/兑换代金券'),
        manual_parameters=[
            openapi.Parameter(
                name='id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='代金券编号'
            ),
            openapi.Parameter(
                name='coupon_code',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='券验证码'
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='为指定VO组领取代金券, 需要有vo组管理权限'
            )
        ],
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        领取/兑换代金券

            http code 200：
            {
                "id": "7873425381443472"
            }
        """
        return CashCouponHandler().draw_cash_coupon(view=self, request=request)
