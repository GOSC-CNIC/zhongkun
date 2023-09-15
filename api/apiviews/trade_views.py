from django.utils.translation import gettext_lazy
from django.conf import settings
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import PaySignGenericViewSet
from api.serializers import trade as trade_serializers
from api.serializers.serializers import PaymentHistorySerializer
from api.handlers.trade_handlers import TradeHandler
from core import errors


class TradeChargeViewSet(PaySignGenericViewSet):
    """
    支付交易视图
    """
    authentication_classes = []
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
                "payment_method": "balance",    # balance(余额支付)；coupon(资源券支付)；balance+coupon(余额+资源券)
                "executor": "",
                "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc", # 支付者id
                "payer_name": "lilei@xx.com",       # 支付者名称
                "payer_type": "user",               # user(支付者是用户)；vo(支付者是VO组)
                "payable_amounts": "1.99",    # 应付金额
                "amounts": "-1.99",         # 余额扣费金额
                "coupon_amount": "0.00",    # 资源券扣费金额
                "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                "payment_time": "2022-07-19T06:08:08.852251Z",      # 支付完成时间，未支付成功时为空
                "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                "status_desc": "",    # 状态描述
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
                "payment_method": "balance",    # balance(余额支付)；coupon(资源券支付)；balance+coupon(余额+资源券)
                "executor": "",
                "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc", # 支付者id
                "payer_name": "lilei@xx.com",       # 支付者名称
                "payer_type": "user",               # user(支付者是用户)；vo(支付者是VO组)
                "payable_amounts": "1.99",    # 应付金额
                "amounts": "-1.99",         # 余额扣费金额
                "coupon_amount": "0.00",    # 资源券扣费金额
                "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                "payment_time": "2022-07-19T06:08:08.852251Z",      # 支付完成时间，未支付成功时为空
                "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                "status_desc": "",    # 状态描述
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
    authentication_classes = []
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('交易记录编号查询交易记录'),
        manual_parameters=[
            openapi.Parameter(
                name='query_refunded',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='请求返回已退款金额信息，此参数不需要值存在有效'
            )
        ],
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
                "payment_method": "balance",    # balance(余额支付)；coupon(资源券支付)；balance+coupon(余额+资源券)
                "executor": "",
                "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc", # 支付者id
                "payer_name": "lilei@xx.com",       # 支付者名称
                "payer_type": "user",               # user(支付者是用户)；vo(支付者是VO组)
                "payable_amounts": "1.99",    # 应付金额
                "amounts": "-1.99",         # 余额扣费金额
                "coupon_amount": "0.00",    # 资源券扣费金额
                "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                "payment_time": "2022-07-19T06:08:08.852251Z",      # 支付完成时间，未支付成功时为空
                "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                "status_desc": "",    # 状态描述
                "remark": "test remark",
                "order_id": "order_id",
                "app_id": "20220719060807",
                "app_service_id": "123",
                "refunded_amounts": "0.00"      # 已退款金额，提交参数query_refunded时此内容才会存在
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
        manual_parameters=[
            openapi.Parameter(
                name='query_refunded',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='请求返回已退款金额信息，此参数不需要值存在有效'
            )
        ],
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
                "payment_method": "balance",    # balance(余额支付)；coupon(资源券支付)；balance+coupon(余额+资源券)
                "executor": "",
                "payer_id": "28b94370-0729-11ed-8d9d-c8009fe2ebbc", # 支付者id
                "payer_name": "lilei@xx.com",       # 支付者名称
                "payer_type": "user",               # user(支付者是用户)；vo(支付者是VO组)
                "payable_amounts": "1.99",    # 应付金额
                "amounts": "-1.99",         # 余额扣费金额
                "coupon_amount": "0.00",    # 资源券扣费金额
                "creation_time": "2022-04-07T07:59:22.695692Z",       # 创建时间
                "payment_time": "2022-07-19T06:08:08.852251Z",      # 支付完成时间，未支付成功时为空
                "status": "success",  # wait: 未支付；success: 成功；error: 支付失败；closed: 交易关闭
                "status_desc": "",    # 状态描述
                "remark": "test remark",
                "order_id": "order_id",
                "app_id": "20220719060807",
                "app_service_id": "123",
                "refunded_amounts": "10.00"      # 已退款金额，提交参数query_refunded时此内容才会存在
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
              "public_key": "-----BEGIN PUBLIC  KEY-----xxx-----END PUBLIC  KEY-----"
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


class TradeRefundViewSet(PaySignGenericViewSet):
    """
    退款交易视图
    """
    authentication_classes = []
    permission_classes = []
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('申请退款'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        申请退款

            http code 200：
            {
                "id": "202212010212042076503331",   # 钱包退款交易编号
                "trade_id": "202212010212033498546649", # 钱包支付交易记录编号
                "out_order_id": "order_id",     # 外部订单编号
                "out_refund_id": "out_refund_id1",  # 外部退款编号
                "refund_reason": "reason1",
                "total_amounts": "100.00",  # 退款对应的交易订单总金额
                "refund_amounts": "10.00",  # 请求退款金额
                "real_refund": "6.00",      # 实际退款金额
                "coupon_refund": "4.00",    # 本次退款资源券占比金额，此金额不退。
                "creation_time": "2022-12-01T02:12:04.207445Z",
                "success_time": "2022-12-01T02:12:04.221869Z",
                "status": "success",    # wait：未退款；success：退款成功；error：退款失败；closed: 交易关闭（未退款时撤销了退款）
                "status_desc": "退款成功",
                "remark": "remark1",
                "owner_id": "8be680b2-711d-11ed-908d-c8009fe2ebbc",
                "owner_name": "lilei@cnic.cn",
                "owner_type": "user"
            }

            http 400, 401，404, 409:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            400：
                BadRequest: 参数有误
                InvalidRemark: 备注信息无效，字符太长。
                InvalidRefundReason：退款原因无效，字符太长。
                InvalidRefundAmount：退款金额无效无效，大于0.01，整数部分最大8位，精确到小数点后2位
                MissingTradeId：订单编号或者订单的交易编号必须提供一个。
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
            404：
                NoSuchTrade：交易记录不存在
                NotOwnTrade: 交易记录不属于你
                NoSuchOutOrderId：订单号交易记录不存在
            409：
                TradeStatusInvalid：非支付成功状态的交易订单无法退款
                RefundAmountsExceedTotal：总退款金额（本次退款和历史已退款）超过了原订单金额
                OutRefundIdExists：退款单号已存在
        """
        return TradeHandler().trade_refund(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('退款查询'),
        manual_parameters=[
            openapi.Parameter(
                name='refund_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('钱包退款交易编号，与外部退款编号 out_refund_id 二选一，同时存在优先使用refund_id')
            ),
            openapi.Parameter(
                name='out_refund_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('应用APP内的退款编号，与钱包退款交易编号 refund_id 二选一')
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query', url_name='refund-query')
    def refund_query(self, request, *args, **kwargs):
        """
        退款查询

            http code 200：
            {
                "id": "202212010212042076503331",   # 钱包退款交易编号
                "trade_id": "202212010212033498546649", # 钱包支付交易记录编号
                "out_order_id": "order_id",     # 外部订单编号
                "out_refund_id": "out_refund_id1",  # 外部退款编号
                "refund_reason": "reason1",
                "total_amounts": "100.00",  # 退款对应的交易订单总金额
                "refund_amounts": "10.00",  # 请求退款金额
                "real_refund": "6.00",      # 实际退款金额
                "coupon_refund": "4.00",    # 本次退款资源券占比金额，此金额不退。
                "creation_time": "2022-12-01T02:12:04.207445Z",
                "success_time": "2022-12-01T02:12:04.221869Z",
                "status": "success",    # wait：未退款；success：退款成功；error：退款失败；closed: 交易关闭（未退款时撤销了退款）
                "status_desc": "退款成功",
                "remark": "remark1",
                "owner_id": "8be680b2-711d-11ed-908d-c8009fe2ebbc",
                "owner_name": "lilei@cnic.cn",
                "owner_type": "user"
            }

            http 400, 401，404:
            {
                "code": "xxx",
                "message": "xxx"
            }

            * 可能的错误码：
            400：
                BadRequest: 参数有误
                MissingTradeId：外部退款单号或者钱包退款的交易编号必须提供一个。
            401:
                NoSuchAPPID：app_id不存在
                AppStatusUnaudited：应用app处于未审核状态
                AppStatusBan: 应用处于禁止状态
                NoSetPublicKey: app未配置RSA公钥
                InvalidSignature: 签名无效
            404：
                NoSuchTrade：交易记录不存在
                NotOwnTrade: 交易记录不属于你
                NoSuchOutRefundId：退款单号交易记录不存在
        """
        return TradeHandler().trade_refund_query(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return trade_serializers.RefundPostSerializer
        elif self.action == 'refund_query':
            return trade_serializers.RefundRecordSerializer

        return Serializer
