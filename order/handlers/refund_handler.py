from django.utils.translation import gettext as _
from django.conf import settings
from rest_framework.response import Response

from core import errors
from core.site_configs_manager import get_pay_app_id
from api.viewsets import CustomGenericViewSet
from order.managers import OrderManager, OrderRefundManager
from api import request_logger


class RefundOrderHandler:

    @staticmethod
    def create_refund(view: CustomGenericViewSet, request, kwargs):
        """
        提交订单退订退款申请
        """
        order_id = request.query_params.get('order_id', None)
        reason = request.query_params.get('reason', '')

        if order_id is None:
            return view.exception_response(
                errors.InvalidArgument(message=_('必须提交退订订单编号')))

        if not order_id or len(order_id) > 36:
            return view.exception_response(
                errors.InvalidArgument(message=_('提交的订单编号无效')))

        if len(reason) > 255:
            return view.exception_response(
                errors.InvalidArgument(message=_('退订原因不能超过255个字符')))

        try:
            app_id = get_pay_app_id(dj_settings=settings, check_valid=True)
            order = OrderManager().get_permission_order(
                order_id=order_id, user=request.user, check_permission=True, read_only=False)
            OrderManager.can_deliver_or_refund_for_order(order)
            refund = OrderRefundManager().create_order_refund(order=order, reason=reason)
        except errors.Error as exc:
            return view.exception_response(exc)

        refund_id = refund.id
        try:
            OrderRefundManager().do_refund(order_refund=refund, app_id=app_id, is_refund_coupon=True)
        except errors.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}')

        return Response(data={
            'refund_id': refund_id
        })
