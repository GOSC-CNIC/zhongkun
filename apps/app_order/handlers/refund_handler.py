from datetime import datetime

from django.utils.translation import gettext as _
from django.conf import settings
from rest_framework.response import Response

from core import errors
from core.site_configs_manager import get_pay_app_id
from apps.api.viewsets import CustomGenericViewSet
from apps.api import request_logger
from utils.time import iso_to_datetime
from apps.app_order.managers import OrderManager, OrderRefundManager
from apps.app_order.models import OrderRefund


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

    def list_refund(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_refund_validate_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        status_in = [data['status']] if data['status'] else None
        if vo_id:
            try:
                queryset = OrderRefundManager().filter_vo_refund_queryset(
                    order_id=data['order_id'],
                    status_in=status_in,
                    time_start=data['time_start'],
                    time_end=data['time_end'],
                    user=user, vo_id=vo_id, is_delete=False
                )
            except Exception as exc:
                return view.exception_response(exc)
        else:
            queryset = OrderRefundManager().filter_refund_qs(
                order_id=data['order_id'],
                status_in=status_in,
                time_start=data['time_start'],
                time_end=data['time_end'],
                user_id=user.id, vo_id=None, is_delete=False
            )
        try:
            results = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=results, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_refund_validate_params(request) -> dict:
        status = request.query_params.get('status', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        vo_id = request.query_params.get('vo_id', None)
        order_id = request.query_params.get('order_id', None)

        if status is not None and status not in OrderRefund.Status.values:
            raise errors.InvalidArgument(message=_('退订状态参数无效'))

        if time_start is not None:
            time_start = iso_to_datetime(time_start)
            if not isinstance(time_start, datetime):
                raise errors.InvalidArgument(message=_('起始日期时间格式无效'))

        if time_end is not None:
            time_end = iso_to_datetime(time_end)
            if not isinstance(time_end, datetime):
                raise errors.InvalidArgument(message=_('截止日期时间格式无效'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('截止时间不得超前起始时间'))

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('指定的vo组ID无效'))

        if order_id is not None and not order_id:
            raise errors.InvalidArgument(message=_('指定的订单编号无效'))

        return {
            'status': status,
            'time_start': time_start,
            'time_end': time_end,
            'vo_id': vo_id,
            'order_id': order_id
        }

    @staticmethod
    def delete_refund(view: CustomGenericViewSet, request, kwargs):
        try:
            OrderRefundManager().delete_refund(refund_id=kwargs[view.lookup_field], user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def cancel_refund(view: CustomGenericViewSet, request, kwargs):
        try:
            OrderRefundManager().cancel_refund(refund_id=kwargs[view.lookup_field], user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=200)
