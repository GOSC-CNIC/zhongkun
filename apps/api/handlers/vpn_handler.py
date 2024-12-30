from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import CustomGenericViewSet
from apps.app_servers.managers import ServerManager
from apps.app_servers import format_who_action_str


class VPNHandler:
    @staticmethod
    def is_need_vpn(service_id: str, user):
        # 确认用户是否需要VPN
        if ServerManager.has_server_in_service(service_id=service_id, user_id=user.id):
            return True
        elif ServerManager.has_vo_server_in_service(service_id=service_id, user=user):
            return True
        else:
            return False

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
        if not VPNHandler.is_need_vpn(service_id=service.id, user=request.user):
            exc = errors.ConflictError(
                message=_('您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户'),
                code='NoResourcesInService'
            )
            return Response(exc.err_data(), status=exc.status_code)

        who_action = format_who_action_str(username=request.user.username)
        try:
            r = view.request_vpn_service(
                service, method='active_vpn', username=request.user.username, who_action=who_action)
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

        who_action = format_who_action_str(username=request.user.username)
        try:
            r = view.request_vpn_service(
                service, method='deactive_vpn', username=request.user.username, who_action=who_action)
        except errors.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except errors.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={})

