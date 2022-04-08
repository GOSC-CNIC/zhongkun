from django.utils.translation import gettext as _
from django.utils import timezone

from core import errors
from api.viewsets import CustomGenericViewSet
from bill.models import PaymentHistory
from bill.managers import PaymentHistoryManager
from order.models import ResourceType
from utils.time import iso_utc_to_datetime


class PaymentHistoryHandler:
    def list_payment_history(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_payment_history_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        user_id = data['user_id']
        time_start = data['time_start']
        time_end = data['time_end']
        payment_type = data['payment_type']
        resource_type = data['resource_type']
        service_id = data['service_id']
        phm = PaymentHistoryManager()
        if view.is_as_admin_request(request=request):
            queryset = phm.get_payment_history_as_admin(
                user=user, user_id=user_id, vo_id=vo_id, time_start=time_start, time_end=time_end,
                _type=payment_type, resource_type=resource_type, service_id=service_id
            )
        elif vo_id:
            queryset = phm.get_vo_payment_history(
                user=user, vo_id=vo_id, time_start=time_start, time_end=time_end,
                _type=payment_type, resource_type=resource_type, service_id=service_id
            )
        else:
            queryset = phm.get_user_payment_history(
                user=user, time_start=time_start, time_end=time_end,
                _type=payment_type, resource_type=resource_type, service_id=service_id
            )

        try:
            orders = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=orders, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_payment_history_validate_params(view, request) -> dict:
        user_id = request.query_params.get('user_id', None)
        vo_id = request.query_params.get('vo_id', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        payment_type = request.query_params.get('payment_type', None)
        resource_type = request.query_params.get('resource_type', None)
        service_id = request.query_params.get('service_id', None)

        now_time = timezone.now()

        if payment_type and payment_type not in PaymentHistory.Type.values:
            raise errors.InvalidArgument(message=_('参数“payment_type”的值无效'))

        if resource_type and resource_type not in ResourceType.values:
            raise errors.InvalidArgument(message=_('参数“resource_type”的值无效'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message=_('参数“user_id”仅以管理员身份查询时允许使用'))

        if user_id is not None and vo_id is not None:
            raise errors.BadRequest(message=_('参数“user_id”和“vo_id”不能同时提交'))

        if time_start is not None:
            time_start = iso_utc_to_datetime(time_start)
            if time_start is None:
                raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))
        else:   # 默认当月起始时间
            time_start = now_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if time_end is not None:
            time_end = iso_utc_to_datetime(time_end)
            if time_end is None:
                raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))
        else:   # 默认当前时间
            time_end = now_time

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))

        # 时间段不得超过一年
        if time_start.replace(year=time_start.year + 1) < time_end:
            raise errors.BadRequest(message=_('起止日期范围不得超过一年'))

        return {
            'user_id': user_id,
            'vo_id': vo_id,
            'time_start': time_start,
            'time_end': time_end,
            'payment_type': payment_type,
            'resource_type': resource_type,
            'service_id': service_id
        }
