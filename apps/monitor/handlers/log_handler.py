from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet

from monitor.models import LogSite, LogSiteTimeReqNum
from monitor.managers.logs import LogSiteManager


class BaseHandler:
    @staticmethod
    def validate_timestamp(st: str):
        if len(st) not in [10, 19]:
            raise errors.BadRequest(message=_('时间戳仅支持10位或19位'))

        try:
            return int(st)
        except ValueError:
            raise errors.BadRequest(message=_('时间戳必须为一个整形数值'))

    def validate_timestamp_range(self, request):
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', None)

        if not start:
            raise errors.BadRequest(message=_('起始时间戳start不能为空。'), code='InvalidStart')
        try:
            start = self.validate_timestamp(start)
        except errors.Error as exc:
            raise errors.BadRequest(message=_('参数start值无效。') + exc.message, code='InvalidStart')

        if not end:
            raise errors.BadRequest(message=_('起始时间戳end不能为空。'), code='InvalidEnd')
        try:
            end = self.validate_timestamp(end)
        except errors.Error as exc:
            raise errors.BadRequest(message=_('参数end值无效。') + exc.message, code='InvalidEnd')

        return {'start': start, 'end': end}

    def validate_loki_query_range_params(self, request):
        """
        :raises: BadRequest
        """
        params = self.validate_timestamp_range(request=request)
        limit = request.query_params.get('limit', 1000)
        direction = request.query_params.get('direction', 'backward')

        try:
            limit = int(limit)
            if limit <= 0:
                raise ValueError
        except ValueError:
            raise errors.BadRequest(message=_('参数limit值必须是一个大于0的整数'), code='InvalidLimit')

        if direction not in ("forward", "backward"):
            raise errors.BadRequest(
                message=_('日志的排序顺序参数direction值无效，可选值为“forward”、“backward”'), code='InvalidDirection')

        params['limit'] = limit
        params['direction'] = direction
        return params


class LogSiteHandler(BaseHandler):
    @staticmethod
    def list_log_site(view: CustomGenericViewSet, request):
        """
        列举日志单元
        """
        log_type = request.query_params.get('log_type', None)
        if log_type:
            if log_type not in LogSite.LogType.values:
                return view.exception_response(
                    errors.InvalidArgument(message=_('指定的日志类型无效')))

        queryset = LogSiteManager.get_perm_log_site_qs(user=request.user, log_type=log_type)
        try:
            sites = view.paginate_queryset(queryset=queryset)
            serializer = view.get_serializer(instance=sites, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    def log_query(self, view: CustomGenericViewSet, request):
        log_site_id = request.query_params.get('log_site_id', None)
        search: str = request.query_params.get('search', None)

        if not log_site_id:
            return view.exception_response(
                errors.BadRequest(message=_('必须指定查询的日志单元'), code='InvalidSiteId'))

        if search and '`' in search:
            return view.exception_response(
                errors.BadRequest(message=_('关键字查询不允许包含字符“`”'), code='InvalidSearch'))

        try:
            params = self.validate_loki_query_range_params(request=request)
            log_site = LogSiteManager.get_log_site(site_id=log_site_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = LogSiteManager().query(
                log_site=log_site, start=params['start'], end=params['end'],
                limit=params['limit'], direction=params['direction'], search=search
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    def list_time_count(self, view: CustomGenericViewSet, request):
        log_site_id = request.query_params.get('log_site_id', None)

        if not log_site_id:
            return view.exception_response(
                errors.BadRequest(message=_('必须指定查询的日志单元'), code='InvalidSiteId'))

        try:
            params = self.validate_timestamp_range(request=request)
            log_site = LogSiteManager.get_log_site(site_id=log_site_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        start = params['start']
        end = params['end']
        ns_base = 10000000000
        if start >= ns_base:    # ns
            start = start // ns_base

        if end >= ns_base:  # ns
            end = end // ns_base
        try:
            queryset = LogSiteTimeReqNum.objects.values('id', 'timestamp', 'count', 'site_id').filter(
                timestamp__gte=start, timestamp__lte=end, site_id=log_site.id, count__gte=0
            ).order_by('-timestamp')
            objs = view.paginate_queryset(queryset=queryset)
            return view.get_paginated_response(objs)
        except errors.Error as exc:
            return view.exception_response(exc)
