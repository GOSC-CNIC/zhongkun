import time
from django.utils.translation import gettext, gettext_lazy as _
from rest_framework.response import Response

from core import errors
from monitor.managers import MonitorJobCephManager, CephQueryChoices


class MonitorCephQueryHandler:
    def query(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        service_id = request.query_params.get('service_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in CephQueryChoices.values:
            return view.exception_response(errors.InvalidArgument(message=_('参数"query"的值无效')))

        if service_id is None:
            return view.exception_response(errors.BadRequest(message=_('参数"service_id"是必须提交的')))

        try:
            self.check_permission(view=view, service_id=service_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobCephManager().query(tag=query, service_id=service_id)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)
    
    def queryrange(self, view, request, kwargs):
        try:
            service_id, query, start, end, step = self.validate_query_range_params(request)
            self.check_permission(view=view, service_id=service_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobCephManager().queryrange(
                tag=query, service_id=service_id, start=start, end=end, step=step)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def check_permission(view, service_id: str, user):
        """
        :return:
            service
        :raises: Error
        """
        try:
            service = view.get_service_by_id(service_id)
        except errors.Error as exc:
            raise exc

        if user.is_federal_admin() or service.user_has_perm(user):     # 服务管理员权限
            return service

        raise errors.AccessDenied(message=gettext('你没有指定服务的管理权限'))

    @staticmethod
    def validate_query_range_params(request):
        """
        :return:
            (service_id: str, query: str, start: int, end: int, step: int)

        :raises: Error
        """
        query = request.query_params.get('query', None)
        service_id = request.query_params.get('service_id', None)
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', int(time.time()))
        step = request.query_params.get('step', 300)

        if query is None:
            raise errors.BadRequest(message=_('参数"query"是必须提交的'))

        if query not in CephQueryChoices.values:
            raise errors.InvalidArgument(message=_('参数"query"的值无效'))

        if service_id is None:
            raise errors.BadRequest(message=_('参数"service_id"是必须提交的'))

        if start is None:
            raise errors.BadRequest(message=_('参数"start"必须提交'))

        try:
            start = int(start)
            if start <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('起始时间"start"的值无效, 请尝试一个正整数'))

        try:
            end = int(end)
            if end <= 0:
                raise ValueError
        except ValueError:
            raise errors.InvalidArgument(message=_('截止时间"end"的值无效, 请尝试一个正整数'))

        timestamp_delta = end - start
        if timestamp_delta < 0:
            raise errors.BadRequest(message=_('截止时间必须大于起始时间'))

        try:
            step = int(step)
        except ValueError:
            raise errors.InvalidArgument(message=_('步长"step"的值无效, 请尝试一个正整数'))

        if step <= 0:
            raise errors.InvalidArgument(message=_('不接受零或负查询解析步长, 请尝试一个正整数'))

        resolution = timestamp_delta // step
        if resolution > 11000:
            raise errors.BadRequest(message=_('超过了每个时间序列11000点的最大分辨率。尝试降低查询分辨率（？step=XX）'))

        return service_id, query, start, end, step
