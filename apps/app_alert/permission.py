from rest_framework.permissions import BasePermission
from apps.app_alert.models import AlertWhiteListModel
from apps.app_alert.utils.utils import hash_md5


class ReceiverPermission(BasePermission):
    """
    Allow ip whitelist
    """

    def has_permission(self, request, view):
        client_ip = self.get_remote_ip(request)
        if AlertWhiteListModel.objects.filter(ip=client_ip).first():
            return True

    @staticmethod
    def get_remote_ip(request):
        remote_addr = request.META['REMOTE_ADDR']
        http_x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if hash_md5(remote_addr) == '3aec3006463da42169cc870cfecc052b':
            return http_x_forwarded_for
        else:
            return remote_addr
