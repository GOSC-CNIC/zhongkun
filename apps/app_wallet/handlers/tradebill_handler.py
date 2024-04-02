from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.exceptions import NotFound

from core import errors
from apps.app_wallet.apiviews import TradeGenericViewSet, PaySignGenericViewSet
from apps.app_wallet.models import TransactionBill
from apps.app_wallet.managers.bill import TransactionBillManager
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

    @staticmethod
    def admin_list_transaction_bills(view: TradeGenericViewSet, request):
        try:
            data = TradeBillHandler.admin_list_transaction_bills_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        admin_user = request.user
        vo_id = data['vo_id']
        user_id = data['user_id']
        time_start = data['time_start']
        time_end = data['time_end']
        trade_type = data['trade_type']
        app_service_id = data['app_service_id']
        tbm = TransactionBillManager()

        try:
            queryset = tbm.admin_transaction_bill_queryset(
                admin_user=admin_user, vo_id=vo_id, user_id=user_id, time_start=time_start, time_end=time_end,
                trade_type=trade_type, app_service_id=app_service_id
            )
        except Exception as exc:
            return view.exception_response(exc)

        try:
            bills = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=bills, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_list_transaction_bills_validate_params(view, request) -> dict:
        user_id = request.query_params.get('user_id', None)
        data = TradeBillHandler.list_transaction_bills_validate_params(view=view, request=request)
        if data['vo_id'] and user_id:
            raise errors.BadRequest(message=_('不能同时查询用户和VO组的流水账单。'))

        data['user_id'] = user_id
        return data

    @staticmethod
    def list_app_transaction_bills(view: PaySignGenericViewSet, request):

        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = TradeBillHandler.list_app_transaction_bills_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        queryset = TransactionBillManager.get_app_transaction_bill_queryset(
            app_id=app.id, time_start=data['trade_time_start'],
            time_end=data['trade_time_end'], trade_type=data['trade_type']
        )

        try:
            bills = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=bills, many=True)
            return view.get_paginated_response(serializer.data)
        except NotFound as exc:
            return view.exception_response(errors.InvalidArgument(str(exc)))
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_app_transaction_bills_validate_params(view, request) -> dict:
        trade_time_start = request.query_params.get('trade_time_start', None)
        trade_time_end = request.query_params.get('trade_time_end', None)
        trade_type = request.query_params.get('trade_type', None)

        if trade_type and trade_type not in TransactionBill.TradeType.values:
            raise errors.InvalidArgument(message=_('参数“trade_type”的值无效'))

        trade_time_start = iso_utc_to_datetime(trade_time_start)
        if trade_time_start is None:
            raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))

        trade_time_end = iso_utc_to_datetime(trade_time_end)
        if trade_time_end is None:
            raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))

        if trade_time_start >= trade_time_end:
            raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))

        # 时间段不得超过一年
        if trade_time_start.replace(year=trade_time_start.year + 1) < trade_time_end:
            raise errors.BadRequest(message=_('起止日期范围不得超过一年'))

        return {
            'trade_time_start': trade_time_start,
            'trade_time_end': trade_time_end,
            'trade_type': trade_type
        }
