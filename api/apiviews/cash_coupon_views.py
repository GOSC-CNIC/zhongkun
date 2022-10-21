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
from api.serializers import trade as trade_serializers
from bill.models import CashCoupon, PayAppService


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
            ),
            openapi.Parameter(
                name='app_service_category',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'服务类别, {PayAppService.Category.choices}'
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
                            "name_en": "怀柔204机房研发测试",
                            "category": "vms-server",
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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('兑换码兑换代金券'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='code',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='兑换码'
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
    @action(methods=['post'], detail=False, url_path='exchange', url_name='exchange-coupon')
    def exchange_coupon(self, request, *args, **kwargs):
        """
        兑换码兑换代金券

            http code 200：
            {
                "id": "7873425381443472"
            }

            http code 400,403,404,409:
            {
                "code": "xxx",
                "message": "xxx"
            }

            400:
                MissingCode: 参数“code”必须指定
                InvalidCode: 兑换码无效
                InvalidVoId: 参数“vo_id”值无效
            403:
                AccessDenied: 没有组管理权限
            404:
                VoNotExist: 项目组不存在
                NoSuchCoupon: 兑换码错误/代金券不存在
            409:
                InvalidCouponCode: 兑换码错误/券验证码错误
                AlreadyCancelled: 代金券已作废
                AlreadyDeleted: 代金券已删除
                AlreadyGranted: 代金券已被领取
        """
        return CashCouponHandler().exchange_cash_coupon(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CashCouponSerializer
        elif self.action == 'list_coupon_payment':
            return serializers.CashCouponPaymentSerializer

        return Serializer


class AdminCashCouponViewSet(CustomGenericViewSet):
    """
    服务单元管理员代金券视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务单元管理员列举代金券'),
        manual_parameters=[
            openapi.Parameter(
                name='app_service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='app子服务可用的券'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'券状态，{CashCoupon.Status.choices}'
            ),
            openapi.Parameter(
                name='template_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='券模板id'
            ),
            openapi.Parameter(
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='以文件形式下载'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        服务单元管理员列举代金券

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
                        },
                        "exchange_code": "771570982053927857"
                    }
                ]
            }
        """
        return CashCouponHandler().admin_list_cash_coupon(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('App服务单元管理员创建一个代金券，可直接发放给指定用户'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        App服务单元管理员创建一个代金券，可直接发放给指定用户

            http code 200：
            {
              "id": "771570982053",
              "face_value": "66.88",
              "creation_time": "2022-10-20T09:01:07.638813Z",
              "effective_time": "2022-10-20T08:52:54.352000Z",
              "expiration_time": "2022-10-26T08:52:54.352000Z",
              "balance": "66.88",
              "status": "available",
              "granted_time": "2022-10-20T09:01:29.623582Z",
              "owner_type": "user",
              "app_service": {
                "id": "s20220623023119",
                "name": "怀柔204机房研发测试",
                "name_en": "怀柔204机房研发测试",
                "category": "vms-server",
                "service_id": "2"
              },
              "user": {
                "id": "1",
                "username": "shun"
              },
              "vo": null,
              "activity": null,
              "exchange_code": "771570982053927857"
            }
        """
        return CashCouponHandler.admin_create_cash_coupon(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.AdminCashCouponSerializer
        elif self.action == 'create':
            return trade_serializers.CashCouponCreateSerializer

        return Serializer
