from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from api.serializers import serializers
from bill.models import PaymentHistory
from bill.managers import PaymentHistoryManager
from utils.time import iso_utc_to_datetime


class PaymentHistoryHandler:
    def list_payment_history(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_payment_history_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        time_start = data['time_start']
        time_end = data['time_end']
        status = data['status']
        app_service_id = data['app_service_id']
        phm = PaymentHistoryManager()
        if vo_id:
            queryset = phm.get_vo_payment_history(
                user=user, vo_id=vo_id, time_start=time_start, time_end=time_end,
                status=status, app_service_id=app_service_id
            )
        else:
            queryset = phm.get_user_payment_history(
                user=user, time_start=time_start, time_end=time_end,
                status=status, app_service_id=app_service_id
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
        status = request.query_params.get('status', None)
        app_service_id = request.query_params.get('app_service_id', None)

        now_time = timezone.now()

        if status and status not in PaymentHistory.Status.values:
            raise errors.InvalidArgument(message=_('参数“status”的值无效'))

        if app_service_id is not None and not app_service_id:
            raise errors.InvalidArgument(message=_('参数“app_service_id”的值无效'))

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
            'status': status,
            'app_service_id': app_service_id
        }

    @staticmethod
    def detail_payment_history(view: CustomGenericViewSet, request, kwargs):
        history_id = kwargs.get(view.lookup_field)
        try:
            payment, coupon_historys = PaymentHistoryManager().get_payment_history_detail(
                payment_id=history_id, user=request.user
            )
            payment_data = serializers.PaymentHistorySerializer(payment).data
            coupon_historys_data = serializers.BaseCashCouponPaymentSerializer(instance=coupon_historys, many=True).data
            payment_data['coupon_historys'] = coupon_historys_data
            return Response(data=payment_data)
        except Exception as exc:
            return view.exception_response(exc)
