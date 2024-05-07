from utils.iprestrict import IPRestrictor
from apps.app_global.configs_manager import IPAccessWhiteListManager


class LinkIPRestrictor(IPRestrictor):
    def load_ip_rules(self):
        return IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.NETBOX_LINK.value)

    @staticmethod
    def clear_cache():
        IPAccessWhiteListManager.clear_cache()

    @staticmethod
    def add_ip_rule(ip_value: str):
        return IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.NETBOX_LINK.value, ip_value=ip_value)

    @staticmethod
    def delete_ip_rules(ip_values: list):
        IPAccessWhiteListManager.delete_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.NETBOX_LINK.value, ip_values=ip_values)
