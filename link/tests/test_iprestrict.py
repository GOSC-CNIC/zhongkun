from django.test import TestCase
from django.conf import settings

from core.errors import AccessDenied
from ..utils.iprestrict import LinkIPRestrictor


class LinkIPRestrictorTests(TestCase):
    def test_ip(self):
        ip_rtcr = LinkIPRestrictor()
        # 允许所有ipv4
        setattr(settings, LinkIPRestrictor.SETTING_KEY_NAME, ['0.0.0.0/0'])
        ip_rtcr.reload_ip_rules()
        self.assertFalse(ip_rtcr.is_restricted(client_ip='0.0.0.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='10.0.0.1'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='192.8.6.100'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='223.8.6.66'))
        self.assertFalse(ip_rtcr.is_restricted(client_ip='255.255.255.255'))

        setattr(
            settings, LinkIPRestrictor.SETTING_KEY_NAME,
            ['192.8.6.100', '223.8.6.100/24', '10.0.0.1 -10.0.1.100']
        )
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
