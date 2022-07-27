from datetime import datetime

from django.utils.translation import gettext as _
from django.conf import settings
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from api.deliver_resource import OrderResourceDeliverer
from order.models import ResourceType, Order, Resource
from order.managers import OrderManager, OrderPaymentManager
from utils.time import iso_to_datetime
from api import request_logger
from servers. managers import ServerManager


CASH_COUPON_BALANCE = 'coupon_balance'


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
    def _pre_pay_order_validate_params(view: CustomGenericViewSet, request, kwargs):
        """
        支付一个订单参数验证
        :raises: Error
        """
        payment_method = request.query_params.get('payment_method', None)
        coupon_ids = request.query_params.getlist('coupon_ids', [])
        order_id: str = kwargs.get(view.lookup_field, '')

        if coupon_ids == []:
            coupon_ids = None

        if len(order_id) != 22:
            raise errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId')

        if not order_id.isdigit():
            raise errors.BadRequest(_('无效的订单编号'), code='InvalidOrderId')

        if payment_method is None:
            raise errors.BadRequest(message=_('支付方式参数“payment_method”'), code='MissingPaymentMethod')

        if payment_method == Order.PaymentMethod.BALANCE.value:
            if coupon_ids:
                raise errors.BadRequest(message=_('仅余额支付方式不能指定代金券'), code='CouponIDsShouldNotExist')
            only_coupon = False
            coupon_ids = []
        elif payment_method == Order.PaymentMethod.CASH_COUPON.value:
            if not coupon_ids:
                raise errors.BadRequest(message=_('仅代金券支付方式必须指定代金券'), code='MissingCouponIDs')
            only_coupon = True
        elif payment_method == CASH_COUPON_BALANCE:
            only_coupon = False
        else:
            raise errors.BadRequest(message=_('支付方式参数“payment_method”值无效'), code='InvalidPaymentMethod')

        if coupon_ids:
            coupon_set = set(coupon_ids)
            if not all(coupon_set):
                raise errors.BadRequest(message=_('参数“coupon_ids”的值不能为空'), code='InvalidCouponIDs')

            if len(coupon_ids) > 5:
                raise errors.BadRequest(message=_('最多可以指定使用5个代金券'), code='TooManyCouponIDs')

            if len(coupon_set) != len(coupon_ids):
                raise errors.BadRequest(message=_('指定的代金券有重复'), code='DuplicateCouponIDExist')

        return order_id, coupon_ids, only_coupon

    @staticmethod
    def _pre_pay_order_check(order: Order, resource: Resource):
        """
        支付订单前的一些检测工作

        :raises: Error
        """
        if order.resource_type == ResourceType.VM.value:
            if order.order_type == Order.OrderType.RENEWAL.value:
                if isinstance(order.start_time, datetime) and isinstance(order.end_time, datetime):
                    if order.start_time >= order.end_time:
                        raise errors.Error(message=_('续费订单续费时长或时段无效。'))

                server = ServerManager.get_server(server_id=resource.instance_id, select_for_update=False)
                OrderResourceDeliverer.check_pre_renewal_server_resource(
                    order=order, server=server
                )

    @staticmethod
    def pay_order(view: CustomGenericViewSet, request, kwargs):
        """
        支付一个订单
        """
        try:
            order_id, coupon_ids, only_coupon = OrderHandler._pre_pay_order_validate_params(
                view=view, request=request, kwargs=kwargs
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            order, resources = OrderManager().get_order_detail(
                order_id=order_id, user=request.user, check_permission=True, read_only=False)
        except errors.Error as exc:
            return view.exception_response(exc)

        resource = resources[0]
        try:
            if order.resource_type not in [ResourceType.VM.value, ResourceType.DISK.value]:
                return view.exception_response(
                    errors.BadRequest(message=_('订单订购的资源类型无效'), code='InvalidResourceType'))

            OrderHandler._pre_pay_order_check(order=order, resource=resource)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            subject = order.build_subject()
            order = OrderPaymentManager().pay_order(
                order=order, app_id=settings.PAYMENT_BALANCE['app_id'], subject=subject,
                executor=request.user.username, remark='',
                coupon_ids=coupon_ids, only_coupon=only_coupon,
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
                order_id=order_id, user=request.user, check_permission=True, read_only=False)
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
