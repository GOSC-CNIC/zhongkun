from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class BaseTradePaySerializer(serializers.Serializer):
    """
    付款扣款
    """
    subject = serializers.CharField(label=_('标题'), max_length=256, required=True)
    order_id = serializers.CharField(label=_('订单ID'), max_length=36, required=True)
    amounts = serializers.DecimalField(
        label=_('金额'), max_digits=10, decimal_places=2, required=True,
        min_value=Decimal('0.01'))
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36, required=True)
    remark = serializers.CharField(label=_('备注信息'), max_length=255, default='')


class TradePaySerializer(BaseTradePaySerializer):
    aai_jwt = serializers.CharField(
        label=_('AAI/科技云通行证用户认证JWT'), required=True, help_text=_('用于指定付款用户，并验证付款用户的有效性')
    )


class TradeChargeSerializer(BaseTradePaySerializer):
    """
    付款扣款
    """
    username = serializers.CharField(
        label=_('AAI/科技云通行证用户名'), max_length=128, required=True,
        help_text=_('用于指定付款用户')
    )


class CashCouponCreateSerializer(serializers.Serializer):
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2)
    effective_time = serializers.DateTimeField(label=_('生效时间'), required=False, help_text=_('默认为当前时间'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'), required=True)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36, required=True)
    username = serializers.CharField(label=_('用户名'), max_length=128, required=False, help_text=_('资源券发给此用户'))
    vo_id = serializers.CharField(label=_('vo组id'), max_length=64, required=False, help_text=_('资源券发给此vo组'))
    remark = serializers.CharField(label=_('备注'), max_length=255, required=False, default='')


class AppServiceSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label='id', max_length=36)
    name = serializers.CharField(label=_('服务名称'), max_length=256)
    name_en = serializers.CharField(label=_('服务英文名称'), max_length=255)
    resources = serializers.CharField(label=_('服务提供的资源'), max_length=128)
    desc = serializers.CharField(label=_('服务描述'), max_length=1024)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    status = serializers.CharField(label=_('服务状态'), max_length=16)
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))
    category = serializers.CharField(label=_('服务类别'), max_length=16)
    orgnazition = serializers.SerializerMethodField(label=_('机构|组织'), method_name='get_orgnazition')
    app_id = serializers.CharField(label=_('应用APP ID'))
    service_id = serializers.CharField(label='服务单元id')

    @staticmethod
    def get_orgnazition(obj):
        if obj.orgnazition:
            return {
                'id': obj.orgnazition.id,
                'name': obj.orgnazition.name,
                'name_en': obj.orgnazition.name_en
            }

        return None


class AppServiceSerializer(AppServiceSimpleSerializer):
    contact_person = serializers.CharField(label=_('联系人名称'), max_length=128)
    contact_email = serializers.EmailField(label=_('联系人邮箱'))
    contact_telephone = serializers.CharField(label=_('联系人电话'), max_length=16)
    contact_fixed_phone = serializers.CharField(label=_('联系人固定电话'), max_length=16)
    contact_address = serializers.CharField(label=_('联系人地址'), max_length=256)


class RefundPostSerializer(serializers.Serializer):
    """
    退款申请
    """
    out_refund_id = serializers.CharField(label=_('外部退款编号'), max_length=64, required=True)
    trade_id = serializers.CharField(
        label=_('钱包支付交易记录编号'), max_length=36, required=False, help_text=_('原支付交易对应的应用APP内的订单编号'))
    out_order_id = serializers.CharField(label=_('订单编号'), max_length=36, required=False)
    refund_amount = serializers.DecimalField(
        label=_('退款金额'), max_digits=10, decimal_places=2, required=True, min_value=Decimal('0.01'))
    refund_reason = serializers.CharField(label=_('退款原因'), max_length=255, required=True)
    remark = serializers.CharField(label=_('备注信息'), max_length=255, default='')


class RefundRecordSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('钱包退款交易编号'), max_length=36)
    trade_id = serializers.CharField(label=_('钱包支付交易记录编号'), max_length=36)
    out_order_id = serializers.CharField(label=_('外部订单编号'), max_length=36)
    out_refund_id = serializers.CharField(label=_('外部退款单编号'), max_length=64)
    refund_reason = serializers.CharField(label=_('退款原因'), max_length=255)
    total_amounts = serializers.DecimalField(label=_('退款对应的交易订单总金额'), max_digits=10, decimal_places=2)
    refund_amounts = serializers.DecimalField(label=_('申请退款金额'), max_digits=10, decimal_places=2)
    real_refund = serializers.DecimalField(label=_('实际退款金额'), max_digits=10, decimal_places=2)
    coupon_refund = serializers.DecimalField(
        label=_('资源券退款金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('资源券或者优惠抵扣金额，此金额不退'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    success_time = serializers.DateTimeField(label=_('退款成功时间'))
    status = serializers.CharField(label=_('退款状态'), max_length=16)
    status_desc = serializers.CharField(label=_('退款状态描述'), max_length=255)
    remark = serializers.CharField(label=_('备注信息'), max_length=256, default='')
    owner_id = serializers.CharField(label=_('所属人ID'), max_length=36, help_text='user id or vo id')
    owner_name = serializers.CharField(label=_('所属人名称'), max_length=255, help_text='username or vo name')
    owner_type = serializers.CharField(label=_('所属人类型'), max_length=8)


class TransactionBillSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('交易流水编号'), max_length=36)
    subject = serializers.CharField(label=_('标题'), max_length=256, default='')
    trade_type = serializers.CharField(label=_('交易类型'), max_length=16)
    trade_id = serializers.CharField(label=_('交易id'), max_length=36, help_text=_('支付、退款、充值ID'))
    out_trade_no = serializers.CharField(
        label=_('外部交易编号'), max_length=64, help_text=_('支付订单号、退款单号'))
    trade_amounts = serializers.DecimalField(
        label=_('交易总金额'), max_digits=10, decimal_places=2, help_text=_('余额+券金额'))
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2, help_text='16.66, -8.88')
    coupon_amount = serializers.DecimalField(label=_('券金额'), max_digits=10, decimal_places=2)
    after_balance = serializers.DecimalField(label=_('交易后余额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    owner_id = serializers.CharField(label=_('所属人ID'), max_length=36, help_text='user id or vo id')
    owner_name = serializers.CharField(label=_('所属人名称'), max_length=255, help_text='username or vo name')
    owner_type = serializers.CharField(label=_('所属人类型'), max_length=8)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36)
    # app_id = serializers.CharField(label=_('应用ID'), max_length=36)
    # account = serializers.CharField(label=_('付款账户'), max_length=36, help_text=_('用户或VO余额ID, 及可能支持的其他账户'))


class AdminTransactionBillSerializer(TransactionBillSerializer):
    operator = serializers.CharField(label=_('交易操作人'), max_length=128, help_text=_('记录此次支付交易是谁执行完成的'))


class AppTransactionBillSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('交易流水编号'), max_length=36)
    subject = serializers.CharField(label=_('标题'), max_length=256, default='')
    trade_type = serializers.CharField(label=_('交易类型'), max_length=16)
    trade_id = serializers.CharField(label=_('交易id'), max_length=36, help_text=_('支付、退款、充值ID'))
    out_trade_no = serializers.CharField(
        label=_('外部交易编号'), max_length=64, help_text=_('支付订单号、退款单号'))
    trade_amounts = serializers.DecimalField(
        label=_('交易总金额'), max_digits=10, decimal_places=2, help_text=_('余额+券金额'))
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2, help_text='16.66, -8.88')
    coupon_amount = serializers.DecimalField(label=_('券金额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36)
    app_id = serializers.CharField(label=_('应用ID'), max_length=36)


class RechargeManualSerializer(serializers.Serializer):
    amount = serializers.DecimalField(label=_('充值总金额'), max_digits=10, decimal_places=2, required=True)
    username = serializers.CharField(
        label=_('充值用户'), max_length=128, required=False, allow_null=True, default=None,
        help_text='向那个用户余额账户充值')
    vo_id = serializers.CharField(
        label=_('充值VO组ID'), max_length=36, required=False, allow_null=True, default=None,
        help_text='向那个vo组余额账户充值')
    remark = serializers.CharField(label=_('备注信息'), max_length=256, allow_blank=True, default='')


class RechargeSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('充值记录编号'), max_length=36)
    trade_channel = serializers.CharField(label=_('交易渠道'), max_length=16)
    out_trade_no = serializers.CharField(label=_('外部交易编号'), max_length=64)
    channel_account = serializers.CharField(label=_('交易渠道账户编号'), max_length=64)
    channel_fee = serializers.DecimalField(label=_('交易渠道费用'), max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(label=_('充值总金额'), max_digits=10, decimal_places=2)
    receipt_amount = serializers.DecimalField(
        label=_('实收金额'), max_digits=10, decimal_places=2, help_text=_('交易渠道中我方账户实际收到的款项'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    success_time = serializers.DateTimeField(label=_('充值成功时间'))
    status = serializers.CharField(label=_('充值状态'), max_length=16)
    status_desc = serializers.CharField(label=_('充值状态描述'), max_length=255)
    in_account = serializers.CharField(
        label=_('入账账户'), max_length=36, help_text=_('用户或VO余额ID, 及可能支持的其他账户'))
    owner_id = serializers.CharField(label=_('所属人ID'), max_length=36, help_text='user id or vo id')
    owner_name = serializers.CharField(label=_('所属人名称'), max_length=255, help_text='username or vo name')
    owner_type = serializers.CharField(label=_('所属人类型'), max_length=8)
    remark = serializers.CharField(label=_('备注信息'), max_length=256)
    executor = serializers.CharField(label=_('交易执行人'), max_length=128, help_text=_('记录此次支付交易是谁执行完成的'))


class PaymentHistorySerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    subject = serializers.CharField(label=_('标题'), max_length=256)
    payment_method = serializers.CharField(label=_('付款方式'), max_length=16)
    executor = serializers.CharField(label=_('交易执行人'), help_text=_('记录此次支付交易是谁执行完成的'))
    payer_id = serializers.CharField(label=_('付款人ID'), help_text='user id or vo id')
    payer_name = serializers.CharField(label=_('付款人名称'), help_text='username or vo name')
    payer_type = serializers.CharField(label=_('付款人类型'), max_length=8)
    payable_amounts = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2)
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    coupon_amount = serializers.DecimalField(label=_('券金额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    payment_time = serializers.DateTimeField(label=_('支付时间'))
    remark = serializers.CharField(label=_('备注信息'), max_length=255)
    status = serializers.CharField(label=_('支付状态'), max_length=16)
    status_desc = serializers.CharField(label=_('支付状态描述'), max_length=255)

    order_id = serializers.CharField(label=_('订单ID'), max_length=36)
    app_id = serializers.CharField(label=_('应用ID'), max_length=36)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36)


class BasePointAccountSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    balance = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class VoPointAccountSerializer(BasePointAccountSerializer):
    vo = serializers.SerializerMethodField(method_name='get_vo')

    @staticmethod
    def get_vo(obj):
        return {'id': obj.vo_id}


class UserPointAccountSerializer(BasePointAccountSerializer):
    user = serializers.SerializerMethodField(method_name='get_user')

    @staticmethod
    def get_user(obj):
        return {'id': obj.user_id}


class CashCouponSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID')
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    effective_time = serializers.DateTimeField(label=_('生效时间'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'))
    balance = serializers.DecimalField(label=_('余额'), max_digits=10, decimal_places=2)
    status = serializers.CharField(label=_('状态'), max_length=16)
    granted_time = serializers.DateTimeField(label=_('领取/发放时间'))
    owner_type = serializers.CharField(label=_('所属类型'), max_length=16)
    app_service = serializers.SerializerMethodField(label=_('适用服务'))
    user = serializers.SerializerMethodField(label=_('用户'))
    vo = serializers.SerializerMethodField(label=_('VO组'))
    activity = serializers.SerializerMethodField(label=_('活动'))
    issuer = serializers.CharField(label=_('发放人'))
    remark = serializers.CharField(label=_('备注'))
    use_scope = serializers.CharField(label=_('使用范围'), max_length=16)
    order_id = serializers.CharField(label=_('订单编号'), max_length=64, help_text=_('适用范围为指定订单时，指定订单编号'))

    @staticmethod
    def get_app_service(obj):
        if obj.app_service is None:
            return None

        return {
            'id': obj.app_service.id,
            'name': obj.app_service.name,
            'name_en': obj.app_service.name_en,
            'category': obj.app_service.category,
            'service_id': obj.app_service.service_id
        }

    @staticmethod
    def get_user(obj):
        if obj.user is None:
            return None

        return {'id': obj.user.id, 'username': obj.user.username}

    @staticmethod
    def get_vo(obj):
        if obj.vo is None:
            return None

        return {'id': obj.vo.id, 'name': obj.vo.name}

    @staticmethod
    def get_activity(obj):
        if obj.activity is None:
            return None

        return {'id': obj.activity.id, 'name': obj.activity.name}


class AdminCashCouponSerializer(CashCouponSerializer):
    exchange_code = serializers.SerializerMethodField(label=_('兑换码'), method_name='get_exchange_code')

    @staticmethod
    def get_exchange_code(obj):
        return obj.one_exchange_code


class BaseCashCouponPaymentSerializer(serializers.Serializer):
    """
    券扣费记录序列化器
    """
    cash_coupon_id = serializers.CharField(label=_('资源券编码'))
    amounts = serializers.DecimalField(label=_('金额'), max_digits=10, decimal_places=2)
    before_payment = serializers.DecimalField(label=_('支付前余额'), max_digits=10, decimal_places=2)
    after_payment = serializers.DecimalField(label=_('支付后余额'), max_digits=10, decimal_places=2)
    creation_time = serializers.DateTimeField(label=_('创建时间'))


class CashCouponPaymentSerializer(BaseCashCouponPaymentSerializer):
    """
    券扣费记录序列化器
    """
    payment_history = PaymentHistorySerializer(allow_null=True)
    refund_history = RefundRecordSerializer(allow_null=True)
