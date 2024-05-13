from rest_framework.permissions import BasePermission
from apps.app_alert.utils.utils import hash_md5

from apps.app_global.configs_manager import IPAccessWhiteListManager
from utils.iprestrict import IPRestrictor


class AlertAPIIPRestrictor(IPRestrictor):
    """
    流量模块 IP 白名单
    """

    def load_ip_rules(self):
        return IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.ALERT.value)

    @staticmethod
    def clear_cache():
        IPAccessWhiteListManager.clear_cache()

    @staticmethod
    def add_ip_rule(ip_value: str):
        return IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.ALERT.value, ip_value=ip_value)

    @staticmethod
    def get_remote_ip(request):
        remote_addr = request.META['REMOTE_ADDR']
        http_x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if hash_md5(remote_addr) == '3aec3006463da42169cc870cfecc052b':
            return http_x_forwarded_for
        else:
            return remote_addr

    def check_restricted(self, request):
        """
        :return:
            ip: str
        :raises: AccessDenied
        """
        client_ip = self.get_remote_ip(request)
        self.is_restricted(client_ip=client_ip)
        return client_ip


class ReceiverPermission(BasePermission):
    """
    Allow ip whitelist
    """

    def has_permission(self, request, view):
        AlertAPIIPRestrictor().check_restricted(request=request)
        return True
