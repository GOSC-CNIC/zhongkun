from django.utils.translation import gettext as _

from core import errors
from .models import LogSite
from .backends.log import LogLokiAPI


class LogSiteManager:
    @staticmethod
    def get_perm_log_site_qs(user, log_type: str):
        queryset = LogSite.objects.select_related(
            'organization', 'site_type').order_by('sort_weight').all()

        if not user.is_federal_admin():
            queryset = queryset.filter(users__id=user.id)

        if log_type:
            queryset = queryset.filter(log_type=log_type)

        return queryset.distinct()

    @staticmethod
    def get_log_site(site_id: str, user):
        """
        查询日志单元，并验证权限

        :return:
            LogSite()

        :raises: Error
        """
        log_site = LogSite.objects.select_related('provider').filter(id=site_id).first()
        if log_site is None:
            raise errors.TargetNotExist(message=_('查询的日志单元不存在。'))

        if user.is_federal_admin():
            return log_site

        if log_site.user_has_perm(user):
            return log_site

        raise errors.AccessDenied(message=_('你没有日志单元的访问权限'))

    @staticmethod
    def query(log_site: LogSite, start: int, end: int, limit: int, direction: str, search: str):
        """
        :return:
            [
                {
                    "metric": {
                    },
                    "values": [
                        [1630267851.781, "log line"]
                    ]
                }
            ]
        :raises: Error
        """
        query = f'{{job = "{log_site.job_tag}"}}'
        if search:
            query = f'{query} |= `{search}`'

        params = {
            'query': query,
            'start': start, 'end': end,
            'limit': limit, 'direction': direction
        }
        return LogLokiAPI().query_log(provider=log_site.provider, querys=params)
