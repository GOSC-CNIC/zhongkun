from django.utils.translation import gettext as _

from core import errors as exceptions
from api.viewsets import CustomGenericViewSet

from monitor.models import LogSite
from monitor.log_managers import LogSiteManager


class LogSiteHandler:
    @staticmethod
    def list_log_site(view: CustomGenericViewSet, request):
        """
        列举日志单元
        """
        log_type = request.query_params.get('log_type', None)
        if log_type:
            if log_type not in LogSite.LogType.values:
                return view.exception_response(
                    exceptions.InvalidArgument(message=_('指定的日志类型无效')))

        queryset = LogSiteManager.get_perm_log_site(user=request.user, log_type=log_type)
        try:
            sites = view.paginate_queryset(queryset=queryset)
            serializer = view.get_serializer(instance=sites, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
