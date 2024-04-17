from django.utils.translation import gettext, gettext_lazy as _
from django.db.models import Q
from rest_framework.response import Response

from core import errors
from apps.monitor.models import MonitorJobTiDB
from apps.monitor.managers.tidb import TiDBQueryChoices, MonitorJobTiDBManager, TiDBQueryV2Choices


class MonitorTiDBQueryHandler:
    @staticmethod
    def get_tidb_monitor_unit(monitor_unit_id: str, user):
        """
        查询tidb监控单元，并验证权限

        :return:
            MonitorJobTiDB()

        :raises: Error
        """
        ceph_unit = MonitorJobTiDB.objects.select_related('org_data_center').filter(id=monitor_unit_id).first()
        if ceph_unit is None:
            raise errors.NotFound(message=_('查询的监控单元不存在。'))

        if user.is_federal_admin():
            return ceph_unit

        qs = MonitorTiDBQueryHandler.has_perm_unit_qs(user_id=user.id)
        if qs.filter(id=monitor_unit_id).exists():
            return ceph_unit

        raise errors.AccessDenied(message=gettext('你没有监控单元的管理权限'))

    @staticmethod
    def list_tidb_unit(view, request):
        """list tidb 监控单元"""
        organization_id = request.query_params.get('organization_id', None)
        user = request.user

        queryset = MonitorJobTiDB.objects.select_related('org_data_center__organization').order_by('-sort_weight').all()
        if organization_id:
            queryset = queryset.filter(org_data_center__organization_id=organization_id)

        if user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(Q(users__id=user.id) | Q(org_data_center__users__id=user.id))

        queryset = queryset.distinct()
        try:
            units = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=units, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    def query(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in TiDBQueryChoices.values:
            return view.exception_response(errors.InvalidArgument(message=_('参数"query"的值无效')))

        if monitor_unit_id is None:
            return view.exception_response(errors.BadRequest(message=_('参数"monitor_unit_id"是必须提交的')))

        try:
            monitor_unit = self.get_tidb_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobTiDBManager().query(tag=query, monitor_unit=monitor_unit)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def has_perm_unit_qs(user_id):
        return MonitorJobTiDB.objects.filter(
            Q(users__id=user_id) | Q(org_data_center__users__id=user_id)
        )

    def query_v2(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('请指定查询指标')))

        if query not in TiDBQueryV2Choices.values:
            return view.exception_response(errors.InvalidArgument(message=_('指定的查询指标的值无效')))

        if monitor_unit_id is None:
            return view.exception_response(errors.BadRequest(message=_('请指定监控单元')))

        try:
            monitor_unit = self.get_tidb_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobTiDBManager().query_v2(tag=query, monitor_unit=monitor_unit)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)
