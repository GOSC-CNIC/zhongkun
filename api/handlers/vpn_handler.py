from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from servers.managers import ServerManager


class VPNHandler:
    @staticmethod
    def active_vpn(view: CustomGenericViewSet, request):
        try:
            service = view.get_service(request, lookup=view.lookup_field, in_='path')
        except errors.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = errors.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        # 确认是否允许激活
        if ServerManager.has_server_in_service(service_id=service.id, user_id=request.user.id):
            pass
        elif ServerManager.has_vo_server_in_service(service_id=service.id, user=request.user):
            pass
        else:
            exc = errors.ConflictError(
                message=_('您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户'),
                code='NoResourcesInService'
            )
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = view.request_vpn_service(service, method='active_vpn', username=request.user.username)
        except errors.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except errors.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={})

    @staticmethod
    def deactive_vpn(view: CustomGenericViewSet, request):
        try:
            service = view.get_service(request, lookup=view.lookup_field, in_='path')
        except errors.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = errors.NoSupportVPN(message=_('服务单元未提供VPN服务'))
            return Response(exc.err_data(), status=exc.status_code)

        try:
            r = view.request_vpn_service(service, method='deactive_vpn', username=request.user.username)
        except errors.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except errors.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={})

