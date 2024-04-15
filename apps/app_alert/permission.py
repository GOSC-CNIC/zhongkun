from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import BasePermission
from apps.app_alert.models import AlertWhiteListModel
from utils.iprestrict import IPRestrictor


class ReceiverPermission(BasePermission):
    """
    Allow ip whitelist
    """

    def has_permission(self, request, view):
        client_ip, proxy_ips = IPRestrictor().get_remote_ip(request)
        if AlertWhiteListModel.objects.filter(ip=client_ip).first():
            return True
