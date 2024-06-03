from django.test import TestCase

from core.errors import AccessDenied
from apps.app_net_manage.models import NetIPAccessWhiteList as IPAccessWhiteList
from apps.app_net_link.permissions import LinkIPRestrictor


class LinkIPRestrictorTests(TestCase):
    def test_ip(self):
        self.assertEqual(IPAccessWhiteList.objects.count(), 0)
        ip_rtcr = LinkIPRestrictor()
        # 允许所有ipv4
        ip_rtcr.add_ip_rule(ip_value='0.0.0.0/0')
        self.assertEqual(IPAccessWhiteList.objects.count(), 1)
        ip_rtcr.clear_cache()
        self.assertFalse(ip_rtcr.is_restricted(client_ip='0.0.0.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='10.0.0.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='192.8.6.100'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='223.8.6.66'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='255.255.255.255'))
        ip_rtcr.delete_ip_rules(ip_values=['0.0.0.0/0'])
        self.assertEqual(IPAccessWhiteList.objects.count(), 0)

        ip_rtcr.add_ip_rule(ip_value='192.8.6.100')
        ip_rtcr.add_ip_rule(ip_value='223.8.6.100/24')
        ip_rtcr.add_ip_rule(ip_value='10.0.0.1 -10.0.1.100')
        self.assertEqual(IPAccessWhiteList.objects.count(), 3)
        ip_rtcr.clear_cache()
        ip_rtcr.reload_ip_rules()
        self.assertFalse(ip_rtcr.is_restricted(client_ip='192.8.6.100'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='10.0.0.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='10.0.1.99'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='223.8.6.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='223.8.6.66'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='223.8.6.255'))
        with self.assertRaises(AccessDenied):
            ip_rtcr.is_restricted(client_ip='0.0.0.1')
        with self.assertRaises(AccessDenied):
            ip_rtcr.is_restricted(client_ip='255.255.255.255')
        with self.assertRaises(AccessDenied):
            ip_rtcr.is_restricted(client_ip='192.8.6.101')
        with self.assertRaises(AccessDenied):
            ip_rtcr.is_restricted(client_ip='223.8.7.1')
        with self.assertRaises(AccessDenied):
            ip_rtcr.is_restricted(client_ip='10.0.1.101')
