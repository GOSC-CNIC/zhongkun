from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import NewPageNumberPagination
from api.handlers.cash_coupon_handler import CashCouponHandler
from api.serializers import serializers


class CashCouponViewSet(CustomGenericViewSet):
    """
    代金券视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举代金券'),
        manual_parameters=[
            openapi.Parameter(
                name='app_service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='app子服务可用的券'
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='列举指定VO组的代金券, 需要有vo组访问权限'
            ),
            openapi.Parameter(
                name='available',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='在有效期内的，未过期的'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举代金券

            http code 200：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 20,
                "results": [
                    {
                        "id": "7873425381443472",
                        "face_value": "666.00",
                        "creation_time": "2022-05-07T06:33:39.496411Z",
                        "effective_time": "2022-05-07T06:32:00Z",
                        "expiration_time": "2022-05-07T06:32:00Z",
                        "balance": "555.00",
                        "status": "available",      # wait：未领取；available：有效；cancelled：作废；deleted：删除
                        "granted_time": "2022-05-07T06:36:31.296470Z",  # maybe None
                        "owner_type": "vo",
                        "app_service": {                                # maybe None
                            "id": "2",
                            "name": "怀柔204机房研发测试",
                            "service_id": "xx"              # maybe None
                        },
                        "user": {                                   # maybe None
                            "id": "1",
                            "username": "shun"
                        },
                        "vo": {                                     # maybe None
                            "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                            "name": "项目组1"
                        },
                        "activity": {                                # maybe None
                            "id": "75b63eee-cda9-11ec-8660-c8009fe2eb10",
                            "name": "test"
                        }
                    }
                ]
            }
        """
        return CashCouponHandler().list_cash_coupon(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('领取/兑换代金券'),
        request_body=no_body,
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除代金券'),
        manual_parameters=[
            openapi.Parameter(
                name='force',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='强制删除，未过期的、有剩余余额的代金券；参数不需要值存在即有效'
            )
        ]
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除代金券

            http code 204
        """
        return CashCouponHandler().delete_cash_coupon(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举代金券扣费记录'),
        manual_parameters=[
            openapi.Parameter(
                name=NewPageNumberPagination.page_query_param,
                required=False,
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='页码'
            ),
            openapi.Parameter(
                name=NewPageNumberPagination.page_size_query_param,
                required=False,
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                description='每页数据数量'
            )
        ]
    )
    @action(methods=['get'], detail=True, url_path='payment', url_name='list-payment')
    def list_coupon_payment(self, request, *args, **kwargs):
        """
        列举代金券扣费记录

            http code 200:
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "creation_time": "2022-07-04T06:07:15.955151Z",
                  "amounts": "-15.97",
                  "before_payment": "1000.00",
                  "after_payment": "984.03",
                  "cash_coupon_id": "144765530930",
                  "payment_history": {
                    "id": "202207040607159512716434",
                    "subject": "云服务器按量计费",
                    "payment_method": "coupon",
                    "executor": "metering",
                    "payer_id": "1",
                    "payer_name": "shun",
                    "payer_type": "user",
                    "amounts": "0.00",
                    "coupon_amount": "-15.97",
                    "payment_time": "2022-07-04T06:07:15.951537Z",
                    "type": "payment",
                    "remark": "server id=0e475786-9ac1-11ec-857b-c8009fe2eb10, 2022-07-03",
                    "order_id": "s-8aa93412fb5f11ec8ac1c8009fe2ebbc",
                    "app_id": "xxx",
                    "app_service_id": "s20220623023119"
                  }
                }
              ]
            }
        """
        return CashCouponHandler().list_cash_coupon_payment(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CashCouponSerializer
        elif self.action == 'list_coupon_payment':
            return serializers.CashCouponPaymentSerializer

        return Serializer
