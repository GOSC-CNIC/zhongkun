from rest_framework.permissions import BasePermission

from apps.app_global.configs_manager import IPAccessWhiteListManager
from utils.iprestrict import IPRestrictor


class ScreenAPIIPRestrictor(IPRestrictor):
    def load_ip_rules(self):
        return IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.SCREEN.value)

    @staticmethod
    def clear_cache():
        IPAccessWhiteListManager.clear_cache()

    @staticmethod
    def add_ip_rule(ip_value: str):
        return IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.SCREEN.value, ip_value=ip_value)


class ScreenAPIIPPermission(BasePermission):
    """
    Allow ip
    """
    def has_permission(self, request, view):
        ScreenAPIIPRestrictor().check_restricted(request=request)
        return True

