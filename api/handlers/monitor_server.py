from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from monitor.managers import MonitorJobServerManager, ServerQueryChoices
from monitor.models import MonitorJobServer


class MonitorServerQueryHandler:
    def query(self, view, request, kwargs):
        query = request.query_params.get('query', None)
        monitor_unit_id = request.query_params.get('monitor_unit_id', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in ServerQueryChoices.values:
            return view.exception_response(errors.InvalidArgument(message=_('参数"query"的值无效')))

        if monitor_unit_id is None:
            return view.exception_response(errors.BadRequest(message=_('参数"monitor_unit_id"是必须提交的')))

        try:
            monitor_unit = self.get_server_monitor_unit(monitor_unit_id=monitor_unit_id, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobServerManager().query(tag=query, monitor_unit=monitor_unit)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def get_server_monitor_unit(monitor_unit_id: str, user):
        """
        查询server监控单元，并验证权限

        :return:
            MonitorJobServer()

        :raises: Error
        """
        monitor_unit = MonitorJobServer.objects.select_related('provider').filter(id=monitor_unit_id).first()
        if monitor_unit is None:
            raise errors.NotFound(message=_('查询的监控单元不存在。'))

        if user.is_federal_admin():
            return monitor_unit

        if monitor_unit.user_has_perm(user):
            return monitor_unit

        raise errors.AccessDenied(message=_('你没有监控单元的管理权限'))
