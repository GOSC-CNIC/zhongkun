from datetime import date

from django.utils.translation import gettext as _
from django.db.models import Subquery

from core import errors
from service.managers import ServiceManager
from servers.managers import ServerManager
from vo.managers import VoManager
from utils.model import OwnerType
from .models import MeteringServer


class MeteringServerManager:
    @staticmethod
    def get_metering_server_queryset():
        return MeteringServer.objects.all()

    def filter_user_server_metering(
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询用户云主机计量用量账单查询集
        """
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, user_id=user.id
        )

    def filter_vo_server_metering(
            self, user,
            vo_id: str,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        return self.filter_server_metering_queryset(
            service_id=service_id, server_id=server_id, date_start=date_start,
            date_end=date_end, vo_id=vo_id
        )

    def filter_server_metering_by_admin(
            self, user,
            service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            vo_id: str = None,
            user_id: str = None
    ):
        """
        查询vo组云主机计量用量账单查询集

        :rasies: AccessDenied, NotFound, Error
        """
        if user.is_federal_admin():
            return self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if server_id:
            server_or_archieve = ServerManager.get_server_or_archive(server_id=server_id)
            if server_or_archieve is None:
                return MeteringServer.objects.none()

            if service_id:
                if service_id != server_or_archieve.service_id:
                    return MeteringServer.objects.none()
            else:
                service_id = server_or_archieve.service_id

        if service_id:
            service = ServiceManager.get_service_if_admin(user=user, service_id=service_id)
            if service is None:
                raise errors.AccessDenied(message=_('您没有指定服务的访问权限'))

        queryset = self.filter_server_metering_queryset(
                service_id=service_id, server_id=server_id, date_start=date_start, date_end=date_end,
                vo_id=vo_id, user_id=user_id
            )

        if not service_id and not server_id:
            qs = ServiceManager.get_all_has_perm_service(user)
            subq = Subquery(qs.values_list('id', flat=True))
            queryset = queryset.filter(service_id__in=subq)

        return queryset

    def filter_server_metering_queryset(
            self, service_id: str = None,
            server_id: str = None,
            date_start: date = None,
            date_end: date = None,
            user_id: str = None,
            vo_id: str = None
    ):
        """
        查询云主机计量用量账单查询集
        """
        if user_id and vo_id:
            raise errors.Error(_('云主机计量用量账单查询集查询条件不能同时包含"user_id"和"vo_id"'))

        lookups = {}
        if date_start:
            lookups['date__gte'] = date_start

        if date_end:
            lookups['date__lte'] = date_end

        if service_id:
            lookups['service_id'] = service_id

        if server_id:
            lookups['server_id'] = server_id

        if user_id:
            lookups['owner_type'] = OwnerType.USER.value
            lookups['user_id'] = user_id

        if vo_id:
            lookups['owner_type'] = OwnerType.VO.value
            lookups['vo_id'] = vo_id

        queryset = self.get_metering_server_queryset()
        return queryset.filter(**lookups).order_by('-creation_time')

