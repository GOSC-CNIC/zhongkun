from urllib import parse

from django.urls import reverse

from servers.models import Flavor
from utils.test import get_or_create_user, get_or_create_service
from . import MyAPITestCase


class FlavorTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()

    def test_get_flavor(self):
        f = Flavor(vcpus=1, ram=1, enable=True, service_id=None)
        f.save(force_insert=True)
        f2 = Flavor(vcpus=2, ram=2, enable=True, service_id=self.service.id)
        f2.save(force_insert=True)

        url = reverse('api:flavor-list')
        response = self.client.get(url, format='json')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        url = reverse('api:flavor-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200)
        flavors = response.data['flavors']
        self.assertIsInstance(flavors, list)
        self.assertEqual(len(flavors), 1)
        self.assert_is_subdict_of(sub={
            'id': f.id, 'vcpus': f.vcpus, 'ram': 1, 'service_id': None, 'ram_gib': 1
        }, d=flavors[0])

        # query param "service_id"
        url = reverse('api:flavor-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        flavors = response.data['flavors']
        self.assertIsInstance(flavors, list)
        self.assertEqual(len(flavors), 1)
        self.assert_is_subdict_of(sub={
            'id': f2.id, 'vcpus': 2, 'ram': 2, 'service_id': self.service.id, 'ram_gib': 2
        }, d=flavors[0])
