from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import TradeGenericViewSet, PaySignGenericViewSet
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


class AppTradeBillViewSet(PaySignGenericViewSet):
    """
    app交易流水视图
    """
    authentication_classes = []
    permission_classes = []
    pagination_class = TradeBillPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询交易流水账单'),
        manual_parameters=[
            openapi.Parameter(
                name='trade_time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'交易时间段起始时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='trade_time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'交易时间段终止时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ'
            ),
            openapi.Parameter(
                name='trade_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'交易类型, {TransactionBill.TradeType.choices}'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询交易流水账单

            * app 查询交易流水账单，RSA密钥签名认证

            http code 200：
            {
              "has_next": false,        # 是否有下一页
              "page_size": 100,         # 每页数据量
              "marker": null,           # 当前页的标记
              "next_marker": null,      # 下一页标记
              "results": [
                {
                  "id": "202212060710188945381211",
                  "subject": "退款测试2",
                  "trade_type": "refund",
                  "trade_id": "202212060710188271051942",
                  "out_trade_no": "",
                  "trade_amounts": "6.00",      # 本次交易总金额
                  "amounts": "1.00",            # 余额金额
                  "coupon_amount": "5.00",      # 券金额
                  "creation_time": "2022-12-06T07:10:18.891763Z",
                  "remark": "string",
                  "app_service_id": "s20220623023119",
                  "app_id": "20220622082141"
                }
              ]
            }

            http 400, 401:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            400：
                BadRequest: 参数有误
                InvalidArgument: 参数值无效。
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
        """
        return TradeBillHandler().list_app_transaction_bills(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return trade_serializers.AppTransactionBillSerializer

        return Serializer


class AdminTradeBillViewSet(TradeGenericViewSet):
    """
    管理员交易流水账单视图
    """
    # authentication_classes = []
    permission_classes = [IsAuthenticated]
    pagination_class = TradeBillPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举交易流水账单'),
        manual_parameters=[
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定VO组的支付记录'
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询指定用户的支付记录'
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
        管理员列举交易流水账单

            * 通过科技云通行证jwt和session认证
            * 联邦管理员可查询所有交易流水
            * app service管理员只能查询有管理权限的app_service的交易流水

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
                        "app_service_id": "app_service2",
                        "operator": "xxx"
                    }
                ]
            }

            http 400, 401, 403:
            {
                "code": "xxx",
                "message": "xxx"
            }
        """
        return TradeBillHandler.admin_list_transaction_bills(view=self, request=request)

    def get_serializer_class(self):
        if self.action == 'list':
            return trade_serializers.AdminTransactionBillSerializer

        return Serializer
