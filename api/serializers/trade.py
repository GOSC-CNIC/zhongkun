from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class TradePaySerializer(serializers.Serializer):
    """
    付款扣款
    """
    subject = serializers.CharField(label=_('标题'), max_length=256, required=True)
    order_id = serializers.CharField(label=_('订单ID'), max_length=36, required=True)
    amounts = serializers.DecimalField(
        label=_('金额'), max_digits=10, decimal_places=2, required=True,
        min_value=Decimal('0.01'))
    app_service_id = serializers.CharField(label=_('APP服务ID'), max_length=36, required=True)
    aai_jwt = serializers.CharField(
        label=_('AAI/科技云通行证用户认证JWT'), required=True, help_text=_('用于指定付款用户，并验证付款用户的有效性')
    )
    remark = serializers.CharField(label=_('备注信息'), max_length=255, default='')