from datetime import date

from django.utils.translation import gettext as _
from django.utils import timezone

from core import errors
from api.viewsets import CustomGenericViewSet
from metering.managers import MeteringServerManager


class MeteringHandler:
    def list_server_metering(self, view: CustomGenericViewSet, request):
        """
        列举云主机计量账单
        """
        try:
            params = self.list_server_metering_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        server_id = params['server_id']
        date_start = params['date_start']
        date_end = params['date_end']
        vo_id = params['vo_id']
        user_id = params['user_id']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):   
            queryset = ms_mgr.filter_server_metering_by_admin(
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id, user_id=user_id
            )
        elif vo_id:     
            queryset = ms_mgr.filter_vo_server_metering(    
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id
            )
        else:           
            queryset = ms_mgr.filter_user_server_metering(
                user=request.user, service_id=service_id, server_id=server_id, date_start=date_start,
                date_end=date_end
            )

        try:
            orders = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=orders, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_server_metering_validate_params(view: CustomGenericViewSet, request) -> dict:
        service_id = request.query_params.get('service_id', None)
        server_id = request.query_params.get('server_id', None)
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        vo_id = request.query_params.get('vo_id', None)
        user_id = request.query_params.get('user_id', None)

        now_date = timezone.now().date()

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        if server_id is not None and not server_id:
            raise errors.InvalidArgument(message=_('参数“server_id”的值无效'))

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:   # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date

        if date_start >= date_end:
            raise errors.BadRequest(message=_('参数“date_start”时间必须超前“date_end”时间'))

        # 时间段不得超过一年
        if date_start.replace(year=date_start.year + 1) < date_end:
            raise errors.BadRequest(message=_('起止日期范围不得超过一年'))

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message=_('参数“user_id”仅以管理员身份查询时允许使用'))

        if user_id is not None and vo_id is not None:
            raise errors.BadRequest(message=_('参数“user_id”和“vo_id”不能同时提交'))

        return {
            'date_start': date_start,
            'date_end': date_end,
            'vo_id': vo_id,
            'service_id': service_id,
            'server_id': server_id,
            'user_id': user_id
        }

    def list_aggregation_by_server(self, view: CustomGenericViewSet, request):
        """
        列举云主机计量计费聚合信息
        """
        try:
            params = self.list_aggregation_by_server_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        date_start = params['date_start']
        date_end = params['date_end']
        user_id = params['user_id']
        service_id = params['service_id']
        vo_id = params['vo_id']

        ms_mgr = MeteringServerManager()
        if view.is_as_admin_request(request):       
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_admin(
                user=request.user, date_start=date_start, date_end=date_end, user_id=user_id,
                service_id=service_id, vo_id=vo_id
            )
        elif vo_id:     
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_vo(
                user=request.user, service_id=service_id, date_start=date_start,
                date_end=date_end, vo_id=vo_id
            )
        else:         
            queryset = ms_mgr.aggregate_server_metering_by_uuid_by_user(
                user=request.user, date_start=date_start, date_end=date_end, service_id=service_id
            )

        try:
            data = view.paginate_queryset(queryset)
            data = ms_mgr.aggregate_by_server_mixin_data(data)
            return view.get_paginated_response(data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def list_aggregation_by_server_validate_params(view: CustomGenericViewSet, request) -> dict:    
        date_start = request.query_params.get('date_start', None)
        date_end = request.query_params.get('date_end', None)
        user_id = request.query_params.get('user_id', None)
        service_id = request.query_params.get('service_id', None)
        vo_id = request.query_params.get('vo_id', None)

        now_date = timezone.now().date()

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('参数“vo_id”的值无效'))

        if date_start is not None:
            try:
                date_start = date.fromisoformat(date_start)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_start”的值无效的日期格式'))
        else:                       # 默认当月起始时间
            date_start = now_date.replace(day=1)

        if date_end is not None:
            try:
                date_end = date.fromisoformat(date_end)
            except (TypeError, ValueError):
                raise errors.InvalidArgument(message=_('参数“date_end”的值无效的日期格式'))
        else:
            date_end = now_date     # 默认当月当前日期

        if user_id is not None and not view.is_as_admin_request(request):
            raise errors.BadRequest(message=_('参数“user_id”仅以管理员身份查询时允许使用'))

        if service_id is not None and not service_id:
            raise errors.InvalidArgument(message=_('参数“service_id”的值无效'))

        if user_id is not None and vo_id is not None:
            raise errors.BadRequest(message=_('参数“user_id”和“vo_id”不能同时提交'))

        return {
            'date_start': date_start,
            'date_end':  date_end,
            'user_id': user_id,
            'service_id': service_id,
            'vo_id': vo_id
        }
