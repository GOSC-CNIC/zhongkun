from django.utils.translation import gettext, gettext_lazy as _

from core import errors
from monitor.models import MonitorJobTiDB


class MonitorTiDBQueryHandler:
    @staticmethod
    def get_tidb_monitor_unit(monitor_unit_id: str, user):
        """
        查询tidb监控单元，并验证权限

        :return:
            MonitorJobTiDB()

        :raises: Error
        """
        ceph_unit = MonitorJobTiDB.objects.select_related('provider').filter(id=monitor_unit_id).first()
        if ceph_unit is None:
            raise errors.NotFound(message=_('查询的监控单元不存在。'))

        if user.is_federal_admin():
            return ceph_unit

        if ceph_unit.user_has_perm(user):
            return ceph_unit

        raise errors.AccessDenied(message=gettext('你没有监控单元的管理权限'))

    @staticmethod
    def list_tidb_unit(view, request):
        """list tidb 监控单元"""
        organization_id = request.query_params.get('organization_id', None)
        user = request.user

        queryset = MonitorJobTiDB.objects.select_related('organization').order_by('-sort_weight').all()
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        if user.is_federal_admin():
            pass
        else:
            queryset = queryset.filter(users__id=user.id)

        try:
            units = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=units, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)


