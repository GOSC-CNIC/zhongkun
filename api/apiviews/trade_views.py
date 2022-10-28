from django.utils.translation import gettext_lazy
from django.conf import settings
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from api.viewsets import PaySignGenericViewSet
from api.serializers import trade as trade_serializers
from api.serializers.serializers import PaymentHistorySerializer
from api.handlers.trade_handlers import TradeHandler
from core import errors


class TradeChargeViewSet(PaySignGenericViewSet):
    """
    支付交易视图
    """
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'

    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('扣费（通过科技云通行证jwt指定付费人）'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=False, url_path='jwt', url_name='jwt')
    def charge_jwt(self, request, *args, **kwargs):
        """
        通过科技云通行证jwt指定付费人进行扣费

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

            http 400, 401, 409:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            400：
                BadRequest: 参数有误
                InvalidJWT: Token is invalid or expired.
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
            409：
                BalanceNotEnough：余额不足
        """
        return TradeHandler().trade_pay(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('扣费（直接通过用户名指定付费人）'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=False, url_path='account', url_name='account')
    def charge_account(self, request, *args, **kwargs):
        """
        直接通过用户名指定付费人进行扣费

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

            http 400, 401, 409:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            400：
                BadRequest: 参数有误
                InvalidJWT: Token is invalid or expired.
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
            404:
                NoSuchBalanceAccount: 指定的付费用户不存在（余额不足）
            409：
                BalanceNotEnough：余额不足
        """
        return TradeHandler().trade_charge(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'charge_jwt':
            return trade_serializers.TradePaySerializer
        elif self.action == 'charge_account':
            return trade_serializers.TradeChargeSerializer

        return Serializer


class TradeQueryViewSet(PaySignGenericViewSet):
    """
    支付交易记录查询视图
    """
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('交易记录编号查询交易记录'),
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'trade/(?P<trade_id>[^/.]+)', url_name='trade-id')
    def trade_query(self, request, *args, **kwargs):
        """
        交易记录编号查询交易记录

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

            http 400, 401, 404:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            404:
                NoSuchTrade: 查询的交易记录不存在
                NotOwnTrade: 交易记录存在，但交易记录不属于你app
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
        """
        return TradeHandler().trade_query_trade_id(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('订单编号查询交易记录'),
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'out-order/(?P<order_id>[^/.]+)', url_name='order-id')
    def trade_query_order_id(self, request, *args, **kwargs):
        """
        订单编号查询交易记录

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

            http 400, 401, 404:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
            404:
                NoSuchTrade: 查询的交易记录不存在
        """
        return TradeHandler().trade_query_order_id(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['trade_query', 'trade_query_order_id']:
            return PaymentHistorySerializer

        return Serializer


class TradeSignKeyViewSet(PaySignGenericViewSet):
    """
    结算验签公钥
    """
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询结算服务验签RSA公钥'),
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=False, url_path=r'public-key', url_name='public-key')
    def get_public_key(self, request, *args, **kwargs):
        """
        查询结算服务验签RSA公钥

            * 同时支持 通行证jwt认证 和 APP RSA加密签名认证

            http code 200:
            {
              "private_key": "-----BEGIN PRIVATE KEY-----xxx-----END PRIVATE KEY-----"
            }
        """
        if not bool(request.user and request.user.is_authenticated):
            try:
                self.check_request_sign(request)
            except errors.Error as exc:
                return self.exception_response(exc)

        private_key = getattr(settings, 'PAYMENT_RSA2048', {}).get('public_key')
        if not private_key:
            return self.exception_response(errors.ConflictError(message='结算服务未配置RSA公钥'))

        return Response(data={'public_key': private_key})
