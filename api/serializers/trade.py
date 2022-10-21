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
        label=_('AAI/科技云通行证用户认证JWT'), max_length=128, required=True,
        help_text=_('用于指定付款用户，并验证付款用户的有效性')
    )


class CashCouponCreateSerializer(serializers.Serializer):
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2)
    effective_time = serializers.DateTimeField(label=_('生效时间'), required=False, help_text=_('默认为当前时间'))
    expiration_time = serializers.DateTimeField(label=_('过期时间'), required=True)
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36, required=True)
    username = serializers.CharField(label=_('用户名'), max_length=128, required=False, help_text=_('代金券发给此用户'))
