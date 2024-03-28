from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from order.serializers import OrderSerializer


class CouponApplyBaseSerializer(serializers.Serializer):
    id = serializers.CharField()
    service_type = serializers.CharField(label=_('服务类型'))
    odc = serializers.SerializerMethodField(label=_('数据中心'), method_name='get_odc')
    service_id = serializers.CharField(label=_('服务单元id'), max_length=36)
    service_name = serializers.CharField(label=_('服务单元名称'), max_length=255)
    service_name_en = serializers.CharField(label=_('服务单元英文名称'), max_length=255)
    # pay_service_id = serializers.CharField(label=_('钱包结算单元id'), max_length=36)
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2)
    expiration_time = serializers.DateTimeField(label=_('过期时间'))

    apply_desc = serializers.CharField(label=_('申请描述'), max_length=255)
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    update_time = serializers.DateTimeField(label=_('更新时间'))
    user_id = serializers.CharField(label=_('申请人id'), max_length=36)
    username = serializers.CharField(label=_('申请人'), max_length=128)
    vo_id = serializers.CharField(label=_('项目组id'), max_length=36)
    vo_name = serializers.CharField(label=_('项目组名称'), max_length=128)
    owner_type = serializers.CharField(label=_('所属类型'), max_length=16)

    status = serializers.CharField(label=_('状态'), max_length=16)
    approver = serializers.CharField(label=_('审批人'), max_length=128)
    reject_reason = serializers.CharField(label=_('拒绝原因'), max_length=255)
    approved_amount = serializers.DecimalField(label=_('审批通过金额'), max_digits=10, decimal_places=2)
    coupon_id = serializers.CharField(label=_('资源券id'), max_length=36)

    @staticmethod
    def get_odc(obj):
        if not obj.odc:
            return None

        return {'id': obj.odc.id, 'name': obj.odc.name, 'name_en': obj.odc.name_en}


class CouponApplySerializer(CouponApplyBaseSerializer):
    order_id = serializers.CharField(label=_('订单ID'), max_length=36)


class CouponDetailSerializer(CouponApplyBaseSerializer):
    order = OrderSerializer(label=_('订单'), allow_null=True)


class CouponApplyUpdateSerializer(serializers.Serializer):
    face_value = serializers.DecimalField(label=_('面额'), max_digits=10, decimal_places=2, required=True)
    expiration_time = serializers.DateTimeField(
        label=_('过期时间'), required=True, help_text='ISO format，2024-03-13T08:47:51Z')
    apply_desc = serializers.CharField(label=_('申请描述'), max_length=255, required=True)
    service_type = serializers.CharField(label=_('服务类型'), required=True)
    service_id = serializers.CharField(
        label=_('服务单元id'), max_length=36, required=False, allow_null=True, default=None)


class CouponApplyCreateSerializer(CouponApplyUpdateSerializer):
    vo_id = serializers.CharField(
        label=_('项目组id'), max_length=36, required=False, help_text=_('为项目组申请'), allow_null=True, default=None)


class OrderCouponApplySerializer(serializers.Serializer):
    apply_desc = serializers.CharField(label=_('申请描述'), max_length=255, required=True)
    order_id = serializers.CharField(label=_('项目组id'), max_length=36, required=True, help_text=_('为项目组申请'))
