from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_service
from . import set_auth_header, MyAPITestCase


class AvailabilityZoneTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.service = get_or_create_service()

    def test_list_azones(self):
        url = reverse('api:availability-zone-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 400)

        query = parse.urlencode(query={'service_id': self.service.id})
        url = f'{url}?{query}'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        zones = response.data['zones']
        if zones:
            self.assertKeysIn(keys=['id', 'name'], container=zones[0])


class VpnAdapterTests(MyAPITestCase):
    def setUp(self):
        set_auth_header(self)
        self.service = get_or_create_service()

    def test_vpn(self):
        from core.request import request_vpn_service

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
