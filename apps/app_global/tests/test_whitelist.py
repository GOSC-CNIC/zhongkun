import ipaddress

from django.test import TestCase

from utils.iprestrict import IPRange
from apps.app_global.configs_manager import IPAccessWhiteListManager


class IPWhiteListTests(TestCase):
    def setUp(self):
        pass

    @staticmethod
    def ip_is_allow(allowed_ips: list, client_ip: str):
        client_ip = ipaddress.IPv4Address(client_ip)
        for ip_rule in allowed_ips:
            if isinstance(ip_rule, IPRange):
                if ip_rule.start <= client_ip <= ip_rule.end:
                    return True
            else:
                if client_ip in ip_rule:
                    return True

        return False

    def test_lock(self):
        ip_wls = IPAccessWhiteListManager.get_module_ip_whitelist(IPAccessWhiteListManager.ModuleName.SCREEN.value)
        self.assertFalse(self.ip_is_allow(allowed_ips=ip_wls, client_ip='159.0.0.1'))

        IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.SCREEN.value, ip_value='159.0.0.0/24'
        )
        IPAccessWhiteListManager.clear_cache()
        ip_wls = IPAccessWhiteListManager.get_module_ip_whitelist(IPAccessWhiteListManager.ModuleName.SCREEN.value)
        self.assertTrue(self.ip_is_allow(allowed_ips=ip_wls, client_ip='159.0.0.1'))

        # 所有功能IP
        IPAccessWhiteListManager.delete_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.SCREEN.value, ip_values=['159.0.0.0/24']
        )
        IPAccessWhiteListManager.clear_cache()
        ip_wls = IPAccessWhiteListManager.get_module_ip_whitelist(IPAccessWhiteListManager.ModuleName.SCREEN.value)
        self.assertFalse(self.ip_is_allow(allowed_ips=ip_wls, client_ip='159.0.0.1'))

        IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.ALL_MODULE.value, ip_value='159.0.0.0/24'
        )
        IPAccessWhiteListManager.clear_cache()
        ip_wls = IPAccessWhiteListManager.get_module_ip_whitelist(IPAccessWhiteListManager.ModuleName.SCREEN.value)
        self.assertTrue(self.ip_is_allow(allowed_ips=ip_wls, client_ip='159.0.0.1'))
