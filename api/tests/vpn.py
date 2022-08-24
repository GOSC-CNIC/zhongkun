from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_service, get_or_create_user
from core.request import request_vpn_service
from . import MyAPITestCase


class VpnAdapterTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.service = get_or_create_service()

    def test_vpn(self):
        vpn_username = 'testvpn'
        r = request_vpn_service(
            service=self.service,
            method='get_vpn_or_create',
            username=vpn_username
        )
        self.assertEqual(r['username'], vpn_username)
        self.assertIs(r['active'], False)

        r = request_vpn_service(
            service=self.service,
            method='active_vpn',
            username=vpn_username
        )
        self.assertIs(r['active'], True)
        self.assertEqual(r['username'], vpn_username)

        r = request_vpn_service(
            service=self.service,
            method='deactive_vpn',
            username=vpn_username
        )
        self.assertEqual(r['username'], vpn_username)
        self.assertIs(r['active'], False)


class VpnTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.client.force_login(self.user)
        self.service = get_or_create_service()

    def test_active_deactive_vpn(self):
        detail_url = reverse('api:vpn-detail', kwargs={'service_id': self.service.id})
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data['active'], False)

        active_url = reverse('api:vpn-active-vpn', kwargs={'service_id': self.service.id})
        r = self.client.get(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

