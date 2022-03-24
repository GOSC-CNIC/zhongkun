from datetime import datetime

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from order.models import ResourceType, Order
from order.managers import OrderManager
from utils.time import iso_to_datetime


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
