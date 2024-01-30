from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class OrderSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('订单编号'))
    order_type = serializers.CharField(label=_('订单类型'))
    status = serializers.CharField(label=_('订单状态'), max_length=16)
    total_amount = serializers.DecimalField(label=_('总金额'), max_digits=10, decimal_places=2, default=0.0)
    pay_amount = serializers.DecimalField(label=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)
    payable_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2)
    balance_amount = serializers.DecimalField(label=_('余额支付金额'), max_digits=10, decimal_places=2)
    coupon_amount = serializers.DecimalField(label=_('券支付金额'), max_digits=10, decimal_places=2)

    service_id = serializers.CharField(label=_('服务id'), max_length=36)
    service_name = serializers.CharField(label=_('服务名称'), max_length=255)
    resource_type = serializers.CharField(label=_('资源类型'), max_length=16)
    instance_config = serializers.JSONField(label=_('资源的规格和配置'))
    period = serializers.IntegerField(label=_('订购时长(月)'))

    payment_time = serializers.DateTimeField(label=_('支付时间'))
    pay_type = serializers.CharField(label=_('付费方式'), max_length=16)

    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=64)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('VO组名'), max_length=256)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    cancelled_time = serializers.DateTimeField(label=_('作废时间'))
    app_service_id = serializers.CharField(label=_('app服务id'), max_length=36)
    number = serializers.IntegerField(label=_('订购资源数量'))


class ResourceSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    order_id = serializers.CharField(label=_('订单编号'))
    resource_type = serializers.CharField(label=_('订单编号'))
    instance_id = serializers.CharField(label=_('资源实例id'), max_length=36)
    instance_status = serializers.CharField(label=_('资源创建结果'))
    delivered_time = serializers.DateTimeField(label=_('资源交付时间'))
    desc = serializers.CharField(label=_('资源交付结果描述'), max_length=255)


class OrderDetailSerializer(OrderSerializer):
    resources = ResourceSerializer(many=True)
