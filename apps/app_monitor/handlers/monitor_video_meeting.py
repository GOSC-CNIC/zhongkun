from django.utils.translation import gettext, gettext_lazy as _
from rest_framework.response import Response

from core import errors
from apps.app_monitor.managers import MonitorJobVideoMeetingManager, VideoMeetingQueryChoices


class MonitorVideoMeetingQueryHandler:
    def query(self, view, request, kwargs):
        query = request.query_params.get('query', None)

        if query is None:
            return view.exception_response(errors.BadRequest(message=_('参数"query"是必须提交的')))

        if query not in VideoMeetingQueryChoices.values:
            return view.exception_response(errors.BadRequest(message=_('参数"query"值无效')))

        try:
            self.check_permission(view=view, user=request.user)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = MonitorJobVideoMeetingManager().query(tag=query)
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data=data, status=200)

    @staticmethod
    def check_permission(view, user):
        """
        :return
            bool
        :raises: Error
        """
        return True
        # if user.is_federal_admin():
        #     return True
        #
        # raise errors.AccessDenied(message=gettext('你没有指定服务的管理权限'))
