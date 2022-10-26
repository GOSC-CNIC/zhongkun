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


class AppServiceSerializer(serializers.Serializer):
    id = serializers.CharField(label='id', max_length=36)
    name = serializers.CharField(label=_('服务名称'), max_length=256)
    name_en = serializers.CharField(label=_('服务英文名称'), max_length=255)
    resources = serializers.CharField(label=_('服务提供的资源'), max_length=128)
    desc = serializers.CharField(label=_('服务描述'), max_length=1024)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    status = serializers.CharField(label=_('服务状态'), max_length=16)
    contact_person = serializers.CharField(label=_('联系人名称'), max_length=128)
    contact_email = serializers.EmailField(label=_('联系人邮箱'))
    contact_telephone = serializers.CharField(label=_('联系人电话'), max_length=16)
    contact_fixed_phone = serializers.CharField(label=_('联系人固定电话'), max_length=16)
    contact_address = serializers.CharField(label=_('联系人地址'), max_length=256)
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))
    category = serializers.CharField(label=_('服务类别'), max_length=16)
    orgnazition = serializers.SerializerMethodField(label=_('机构|组织'), method_name='get_orgnazition')
    app_id = serializers.CharField(label=_('应用APP ID'))
    # user = serializers.ForeignKey(label=_('用户'))
    # service = serializers.OneToOneField(label=_('对应的VMS服务'))

    @staticmethod
    def get_orgnazition(obj):
        if obj.orgnazition:
            return {
                'id': obj.orgnazition.id,
                'name': obj.orgnazition.name,
                'name_en': obj.orgnazition.name_en
            }

        return None
