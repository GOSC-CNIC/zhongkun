from datetime import datetime

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from api.deliver_resource import OrderResourceDeliverer
from order.models import ResourceType, Order
from order.managers import OrderManager
from bill.managers import PaymentManager
from utils.time import iso_to_datetime
from api import request_logger


class OrderHandler:
    def list_order(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_order_validate_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        if vo_id:
            try:
                queryset = OrderManager().filter_vo_order_queryset(
                    resource_type=data['resource_type'],
                    order_type=data['order_type'],
                    status=data['status'],
                    time_start=data['time_start'],
                    time_end=data['time_end'],
                    user=user,
                    vo_id=vo_id
                )
            except Exception as exc:
                return view.exception_response(exc)
        else:
            queryset = OrderManager().filter_order_queryset(
                resource_type=data['resource_type'],
                order_type=data['order_type'],
                status=data['status'],
                time_start=data['time_start'],
                time_end=data['time_end'],
                user_id=user.id
            )
        try:
            orders = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=orders, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_order_validate_params(request) -> dict:
        resource_type = request.query_params.get('resource_type', None)
        order_type = request.query_params.get('order_type', None)
        status = request.query_params.get('status', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        vo_id = request.query_params.get('vo_id', None)

        if resource_type is not None and resource_type not in ResourceType.values:
            raise errors.InvalidArgument(message=_('参数“resource_type”的值无效'))

        if order_type is not None and order_type not in Order.OrderType.values:
            raise errors.InvalidArgument(message=_('参数“order_type”的值无效'))

        if status is not None and status not in Order.Status.values:
            raise errors.InvalidArgument(message=_('参数“status”的值无效'))

        if time_start is not None:
            time_start = iso_to_datetime(time_start)
            if not isinstance(time_start, datetime):
                raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))

        if time_end is not None:
            time_end = iso_to_datetime(time_end)
            if not isinstance(time_end, datetime):
                raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        return {
            'resource_type': resource_type,
            'order_type': order_type,
            'status': status,
            'time_start': time_start,
            'time_end': time_end,
            'vo_id': vo_id
        }

    @staticmethod
    def order_detail(view: CustomGenericViewSet, request, kwargs):
        order_id: str = kwargs.get(view.lookup_field, '')
        if len(order_id) != 22:
            return view.exception_response(errors.BadRequest(_('无效的订单编号')))

        if not order_id.isdigit():
            return view.exception_response(errors.BadRequest(_('无效的订单编号')))

        try:
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        order.resources = resources
        serializer = view.get_serializer(instance=order)
        return Response(data=serializer.data)

    @staticmethod
    def pay_order(view: CustomGenericViewSet, request, kwargs):
        """
        支付一个订单
        """
        payment_method = request.query_params.get('payment_method', None)
        order_id: str = kwargs.get(view.lookup_field, '')
        if len(order_id) != 22:
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        if not order_id.isdigit():
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        if payment_method is None:
            return view.exception_response(
                errors.BadRequest(message=_('支付方式参数“payment_method”'), code='MissingPaymentMethod'))

        if payment_method == Order.PaymentMethod.VOUCHER.value:
            return view.exception_response(
                errors.BadRequest(message=_('暂不支持代金卷支付方式'), code='InvalidPaymentMethod'))
        if payment_method not in [Order.PaymentMethod.BALANCE.value, Order.PaymentMethod.VOUCHER.value]:
            return view.exception_response(
                errors.BadRequest(message=_('支付方式参数“payment_method”值无效'), code='InvalidPaymentMethod'))

        try:
            order, resources = OrderManager().get_order_detail(
                order_id=order_id, user=request.user, check_permission=True)
        except errors.Error as exc:
            return view.exception_response(exc)

        if order.resource_type not in [ResourceType.VM.value, ResourceType.DISK.value]:
            return view.exception_response(
                errors.BadRequest(message=_('订单订购的资源类型无效'), code='InvalidResourceType'))

        resource = resources[0]
        try:
            order = PaymentManager().pay_order(
                order=order, executor=request.user.username, remark='',
                coupon_ids=[], only_coupon=False,
                required_enough_balance=True
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            OrderResourceDeliverer().deliver_order(order=order, resource=resource)
        except errors.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}')

        return Response(data={
            'order_id': order.id
        })

    @staticmethod
    def claim_order_resource(view: CustomGenericViewSet, request, kwargs):
        """
        订单支付后，自动交付订单资源失败后，尝试索要订单资源
        """
        order_id: str = kwargs.get(view.lookup_field, '')
        if len(order_id) != 22:
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        if not order_id.isdigit():
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        try:
            order, resources = OrderManager().get_order_detail(
                order_id=order_id, user=request.user, check_permission=True)
        except errors.Error as exc:
            return view.exception_response(exc)

        if order.resource_type not in [ResourceType.VM.value, ResourceType.DISK.value]:
            return view.exception_response(
                errors.BadRequest(message=_('订单订购的资源类型无效'), code='InvalidResourceType'))

        resource = resources[0]
        try:
            OrderResourceDeliverer().deliver_order(order=order, resource=resource)
        except errors.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}')
            return view.exception_response(exc)

        return Response(data={
            'order_id': order.id
        })

    @staticmethod
    def cancel_order(view: CustomGenericViewSet, request, kwargs):
        """
        取消未支付订单
        """
        order_id: str = kwargs.get(view.lookup_field, '')
        if len(order_id) != 22:
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        if not order_id.isdigit():
            return view.exception_response(errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId'))

        try:
            order = OrderManager().cancel_order(order_id=order_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={
            'order_id': order.id
        })
