from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import NewPageNumberPagination
from api.handlers.cash_coupon_handler import CashCouponHandler, QueryCouponValidChoices
from api.serializers import serializers
from api.serializers import trade as trade_serializers
from bill.models import CashCoupon, PayAppService
from utils.paginators import NoPaginatorInspector


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
                name='valid',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'筛选条件，{QueryCouponValidChoices.choices}；不提交此参数(全部)'
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
                        },
                        "issuer": "test@cnic.cn"
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
                    "payable_amounts": "160.00",    # 应付金额
                    "amounts": "-60.00",           # 余额支付金额
                    "coupon_amount": "-100.00",   # 代金券支付金额
                    "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                    "payment_time": "2022-04-07T07:59:23.598408Z",        # 支付完成时间，未支付成功时为空
                    "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                    "status_desc": "",    # 状态描述
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
                InvalidCoupon: 代金券无效，没有绑定适用的APP子服务。
                NotAllowToVo: 绑定的适用APP子服务类型为云主机服务的代金券才允许VO组兑换。
        """
        return CashCouponHandler().exchange_cash_coupon(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询代金券详情'),
        request_body=no_body,
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询代金券详情

            Http Code 200 OK:
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
                },
                "issuer": "test@cnic.cn"
            }
        """
        return CashCouponHandler().detail_cash_coupon(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
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
        operation_summary=gettext_lazy('管理员列举代金券'),
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
                name='valid_status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'筛选条件，{QueryCouponValidChoices.choices}；不提交此参数(全部)'
            ),
            openapi.Parameter(
                name='issuer',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'筛选条件，查询指定发放人的券'
            ),
            openapi.Parameter(
                name='redeemer',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'筛选条件，查询指定兑换人的券'
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
                name='download',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='以文件形式下载，不需要值'
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
                        "exchange_code": "771570982053927857",
                        "issuer": "test@cnic.cn"
                    }
                ]
            }
        """
        return CashCouponHandler().admin_list_cash_coupon(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('App服务单元管理员创建一个代金券，可直接发放给指定用户或VO'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        App服务单元管理员、联邦管理员 创建一个代金券，可直接发放给指定用户或vo

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
              "exchange_code": "771570982053927857",
              "issuer": "test@cnic.cn"
            }
        """
        return CashCouponHandler.admin_create_cash_coupon(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员删除代金券'),
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除代金券，联邦管理员，或者券所绑定的APP子服务管理员

            http code 204 OK: 无数据

            http code 401, 403,404:
            {
                "code": "xxx",
                "message": "xxx"
            }

            401:
                NotAuthenticated: 身份未认证
            403:
                AccessDenied: 没有管理权限
            404:
                NoSuchCoupon: 代金券不存在
        """
        return CashCouponHandler.admin_delete_cash_coupon(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员查询代金券详情'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        管理员查询代金券详情，联邦管理员，或者券所绑定的APP子服务管理员

            http code 200 OK:
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
                "exchange_code": "771570982053927857",
                "issuer": "test@cnic.cn"
            }

            http code 401, 403,404:
            {
                "code": "xxx",
                "message": "xxx"
            }

            401:
                NotAuthenticated: 身份未认证
            403:
                AccessDenied: 没有管理权限
            404:
                NoSuchCoupon: 代金券不存在
        """
        return CashCouponHandler.admin_detail_cash_coupon(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举代金券扣费记录'),
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
        管理员列举代金券扣费记录，联邦管理员，或者券所绑定的APP子服务管理员

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
                    "payable_amounts": "160.00",    # 应付金额
                    "amounts": "-60.00",           # 余额支付金额
                    "coupon_amount": "-100.00",   # 代金券支付金额
                    "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                    "payment_time": "2022-04-07T07:59:23.598408Z",        # 支付完成时间，未支付成功时为空
                    "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                    "status_desc": "",    # 状态描述
                    "remark": "server id=0e475786-9ac1-11ec-857b-c8009fe2eb10, 2022-07-03",
                    "order_id": "s-8aa93412fb5f11ec8ac1c8009fe2ebbc",
                    "app_id": "xxx",
                    "app_service_id": "s20220623023119"
                  }
                }
              ]
            }
        """
        return CashCouponHandler().admin_list_cash_coupon_payment(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管查询代金券统计信息'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='app_service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'钱包app服务单元id'
            ),
        ]
    )
    @action(methods=['get'], detail=False, url_path='statistics', url_name='statistics')
    def coupon_statistics(self, request, *args, **kwargs):
        """
        联邦管理员查询代金券统计信息

            http code 200:
            {
              "total_face_value": 27061772.85,  # 代金券总发放点数；时间段和app服务单元参数 有效
              "total_count": 2471,              # 代金券总发放张数；时间段和app服务单元参数 有效
              "redeem_count": 756,              # 代金券已兑换张数；时间段和app服务单元参数 有效
              "available_count": 123            # 当前有效代金券张数；时间段和app服务单元参数 有效
              "coupon_pay_amounts": 8371044.27, # 代金券消耗点数；时间段和app服务单元参数 有效
              "total_balance": 15063204.85      # 代金券总余额点数；app服务单元参数 有效
            }
        """
        return CashCouponHandler().admin_cash_coupon_statistics(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管查询代金券发放人统计信息'),
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='issuer',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'发放代金券的人'
            ),
        ]
    )
    @action(methods=['get'], detail=False, url_path='aggregation/issue', url_name='aggregation-issue')
    def coupon_issue_statistics(self, request, *args, **kwargs):
        """
        联邦管查询代金券发放人统计信息

            http code 200:
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "issuer": "test@cnic.cn",
                  "total_face_value": 27000,
                  "total_count": 3
                }
              ]
            }
        """
        return CashCouponHandler().admin_coupon_issue_statistics(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管查询用户代金券统计信息'),
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='username',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'用户名'
            ),
        ]
    )
    @action(methods=['get'], detail=False, url_path='aggregation/user', url_name='aggregation-user')
    def coupon_user_statistics(self, request, *args, **kwargs):
        """
        联邦管查询用户代金券统计信息

            http code 200:
            {
              "count": 389,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "user_id": "0074c43596f73a33457389221783c060",
                  "username": "948145076@qq.com",
                  "total_face_value": 400,      # 券总面值额，包括已删除的券
                  "total_balance": 209.92,      # 券余额总数，包括已删除的券
                  "total_count": 2,             # 券总数，包括已删除的券
                  "total_usage_count": 0        # 当前有效券总数
                }
             ]
            }
        """
        return CashCouponHandler().admin_coupon_user_statistics(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管查询VO组代金券统计信息'),
        manual_parameters=[
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段起，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'时间段止，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='voname',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'vo组名'
            ),
        ]
    )
    @action(methods=['get'], detail=False, url_path='aggregation/vo', url_name='aggregation-vo')
    def coupon_vo_statistics(self, request, *args, **kwargs):
        """
        联邦管查询VO组代金券统计信息

            http code 200:
            {
              "count": 389,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "vo_id": "9af3460e-59ca-11ed-9fb2-c8009fe2eb03",
                  "name": "AIOPS学生组",
                  "total_face_value": 400,      # 券总面值额，包括已删除的券
                  "total_balance": 209.92,      # 券余额总数，包括已删除的券
                  "total_count": 2,             # 券总数，包括已删除的券
                  "total_usage_count": 0        # 当前有效券总数
                }
             ]
            }
        """
        return CashCouponHandler().admin_coupon_vo_statistics(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return serializers.AdminCashCouponSerializer
        elif self.action == 'create':
            return trade_serializers.CashCouponCreateSerializer
        elif self.action == 'list_coupon_payment':
            return serializers.CashCouponPaymentSerializer

        return Serializer
