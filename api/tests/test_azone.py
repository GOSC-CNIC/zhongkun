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
            self.assertKeysIn(keys=['id', 'name', 'available'], container=zones[0])
