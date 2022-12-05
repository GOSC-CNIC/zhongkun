from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response

from core import errors
from api.viewsets import TradeGenericViewSet
from api.serializers import serializers
from bill.models import TransactionBill
from bill.managers.bill import TransactionBillManager
from utils.time import iso_utc_to_datetime


class TradeBillHandler:
    @staticmethod
    def list_transaction_bills(view: TradeGenericViewSet, request):
        try:
            data = TradeBillHandler.list_transaction_bills_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        time_start = data['time_start']
        time_end = data['time_end']
        trade_type = data['trade_type']
        app_service_id = data['app_service_id']
        tbm = TransactionBillManager()
        if vo_id:
            try:
                queryset = tbm.get_vo_transaction_bill_queryset(
                    user=user, vo_id=vo_id, time_start=time_start, time_end=time_end,
                    trade_type=trade_type, app_service_id=app_service_id
                )
            except Exception as exc:
                return view.exception_response(exc)
        else:
            queryset = tbm.get_user_transaction_bill_queryset(
                user=user, time_start=time_start, time_end=time_end,
                trade_type=trade_type, app_service_id=app_service_id
            )

        try:
            bills = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=bills, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_transaction_bills_validate_params(view, request) -> dict:
        vo_id = request.query_params.get('vo_id', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        trade_type = request.query_params.get('trade_type', None)
        app_service_id = request.query_params.get('app_service_id', None)

        now_time = timezone.now()

        if trade_type and trade_type not in TransactionBill.TradeType.values:
            raise errors.InvalidArgument(message=_('参数“trade_type”的值无效'))

        if app_service_id is not None and not app_service_id:
            raise errors.InvalidArgument(message=_('参数“app_service_id”的值无效'))

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
            'vo_id': vo_id,
            'time_start': time_start,
            'time_end': time_end,
            'trade_type': trade_type,
            'app_service_id': app_service_id
        }
