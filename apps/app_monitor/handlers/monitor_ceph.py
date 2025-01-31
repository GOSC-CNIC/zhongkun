import time
from django.utils.translation import gettext, gettext_lazy as _
from django.db.models import Q
from rest_framework.response import Response

from core import errors
from apps.app_monitor.managers import MonitorJobCephManager, CephQueryChoices, CephQueryV2Choices
from apps.app_monitor.models import MonitorJobCeph


class MonitorCephQueryHandler:
    def query(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in CephQueryChoices.values:
            return view.exception_response(errors.InvalidArgument(message=_('参数"query"的值无效')))

        if monitor_unit_id is None:
            return view.exception_response(errors.BadRequest(message=_('参数"monitor_unit_id"是必须提交的')))

        try:
            monitor_unit = self.get_ceph_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobCephManager().query(tag=query, monitor_unit=monitor_unit)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)
    
    def queryrange(self, view, request, kwargs):
        try:
            monitor_unit_id, query, start, end, step = self.validate_query_range_params(request)
            monitor_unit = self.get_ceph_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobCephManager().queryrange(
                tag=query, monitor_unit=monitor_unit, start=start, end=end, step=step)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def get_ceph_monitor_unit(monitor_unit_id: str, user):
        """
        查询ceph监控单元，并验证权限

        :return:
            MonitorJobCeph()

        :raises: Error
        """
        ceph_unit: MonitorJobCeph = MonitorJobCeph.objects.select_related(
            'org_data_center').filter(id=monitor_unit_id).first()
        if ceph_unit is None:
            raise errors.NotFound(message=_('查询的监控单元不存在。'))

        if user.is_federal_admin():
            return ceph_unit

        qs = MonitorCephQueryHandler.has_perm_unit_qs(user_id=user.id)
        if qs.filter(id=monitor_unit_id).exists():
            return ceph_unit

        raise errors.AccessDenied(message=gettext('你没有监控单元的管理权限'))

    @staticmethod
    def validate_query_range_params(request):
        """
        :return:
            (service_id: str, query: str, start: int, end: int, step: int)

        :raises: Error
        """
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)
        start = request.query_params.get('start', None)
        end = request.query_params.get('end', int(time.time()))
        step = request.query_params.get('step', 300)

        if query is None:
            raise errors.BadRequest(message=_('参数"query"是必须提交的'))

        if query not in CephQueryChoices.values:
            raise errors.InvalidArgument(message=_('参数"query"的值无效'))

        if monitor_unit_id is None:
            raise errors.BadRequest(message=_('参数"monitor_unit_id"是必须提交的'))

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

        return monitor_unit_id, query, start, end, step

    @staticmethod
    def list_ceph_unit(view, request):
        """list ceph 监控单元"""
        organization_id = request.query_params.get('organization_id', None)
        user = request.user

        queryset = MonitorJobCeph.objects.select_related('org_data_center__organization').order_by('-sort_weight').all()
        if organization_id:
            queryset = queryset.filter(org_data_center__organization_id=organization_id)

        if user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(Q(users__id=user.id) | Q(org_data_center__users__id=user.id))

        queryset = queryset.distinct()
        try:
            meterings = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=meterings, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def has_perm_unit_qs(user_id):
        return MonitorJobCeph.objects.filter(
            Q(users__id=user_id) | Q(org_data_center__users__id=user_id)
        )

    def query_v2(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('请指定查询指标')))

        if query not in CephQueryV2Choices.values:
            return view.exception_response(errors.InvalidArgument(message=_('指定的查询指标的值无效')))

        if monitor_unit_id is None:
            return view.exception_response(errors.BadRequest(message=_('请指定监控单元')))

        try:
            monitor_unit = self.get_ceph_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobCephManager().query_v2(tag=query, monitor_unit=monitor_unit)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)
