from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import BasePermission
import socket
from apps.app_alert.models import AlertWhiteListModel


class ReceiverPermission(BasePermission):
    """
    Allow ip whitelist
    """

    def has_permission(self, request, view):
        request_ip = self.get_remote_ip(request)
        if AlertWhiteListModel.objects.filter(ip=request_ip).first():
            return True

    @staticmethod
    def get_remote_ip(request):
        host_name = socket.gethostbyname(socket.gethostname())
        remote_addr = request.META['REMOTE_ADDR']
        http_x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if remote_addr == host_name:
            return http_x_forwarded_for
        else:
            return remote_addr
