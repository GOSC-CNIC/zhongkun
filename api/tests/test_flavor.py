from urllib import parse

from django.urls import reverse

from servers.models import Flavor
from service.models import ServiceConfig
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


class AdminFlavorTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()

    def test_create_flavor(self):
        url = reverse('api:admin-flavor-list')
        response = self.client.post(url, format='json')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        response = self.client.post(url, data={'vcpus': -1, 'ram': 6, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidCPUs', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': -1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidRam', response=response)
        response = self.client.post(url, data={'vcpus': 12345, 'ram': 6, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidCPUs', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 12345, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidRam', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=404, code='ServiceNotExist', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': self.service.id})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin ok
        self.service.users.add(self.user)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 2, 'enable': 'true', 'service_id': self.service.id})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'vcpus', 'ram', 'service_id', 'disk', 'flavor_id', 'enable'], response.data)
        self.assertEqual(response.data['vcpus'], 1)
        self.assertEqual(response.data['ram'], 2)
        self.assertEqual(response.data['service_id'], self.service.id)
        self.assertEqual(response.data['enable'], True)

        # federal admin ok
        self.service.users.remove(self.user)
        response = self.client.post(url, data={'vcpus': 6, 'ram': 8, 'enable': 'false', 'service_id': self.service.id})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.user.set_federal_admin()
        response = self.client.post(url, data={'vcpus': 6, 'ram': 8, 'enable': 'false', 'service_id': self.service.id})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'vcpus', 'ram', 'service_id', 'disk', 'flavor_id', 'enable'], response.data)
        self.assertEqual(response.data['vcpus'], 6)
        self.assertEqual(response.data['ram'], 8)
        self.assertEqual(response.data['service_id'], self.service.id)
        self.assertEqual(response.data['enable'], False)

    def test_list_flavor(self):
        url = reverse('api:admin-flavor-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)

        f6 = Flavor(vcpus=6, ram=8, enable=True, service_id=None)
        f6.save(force_insert=True)
        f1 = Flavor(vcpus=1, ram=4, enable=True, service_id=self.service.id)
        f1.save(force_insert=True)
        f3 = Flavor(vcpus=3, ram=5, enable=False, service_id=self.service.id)
        f3.save(force_insert=True)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)

        # AccessDenied
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        query = parse.urlencode(query={'service_id': 'notfound'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin
        self.service.users.add(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(response.data['results'][0]['id'], f1.id)
        self.assertEqual(response.data['results'][1]['id'], f3.id)

        # query service_id
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(response.data['results'][0]['id'], f1.id)
        self.assertEqual(response.data['results'][1]['id'], f3.id)

        # query enable
        query = parse.urlencode(query={'enable': 'true'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(response.data['results'][0]['id'], f1.id)

        # federal admin, query enable
        self.user.set_federal_admin()
        url = reverse('api:admin-flavor-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['results'][0]['id'], f1.id)
        self.assertEqual(response.data['results'][1]['id'], f3.id)
        self.assertEqual(response.data['results'][2]['id'], f6.id)

        # query enable
        query = parse.urlencode(query={'enable': 'true'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], f1.id)
        self.assertEqual(response.data['results'][1]['id'], f6.id)

        # query service_id
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['id'], f1.id)
        self.assertEqual(response.data['results'][1]['id'], f3.id)

        # query service_id, enable
        query = parse.urlencode(query={'service_id': self.service.id, 'enable': 'false'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], f3.id)

    def test_update_flavor(self):
        service2 = ServiceConfig(name='test2', name_en='test2 en')
        service2.save(force_insert=True)
        f6 = Flavor(vcpus=6, ram=8, enable=True, service_id=None)
        f6.save(force_insert=True)
        f1 = Flavor(vcpus=1, ram=4, enable=True, service_id=self.service.id)
        f1.save(force_insert=True)

        url = reverse('api:admin-flavor-update', kwargs={'id': 'xxx'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        response = self.client.post(url, data={'vcpus': -1, 'ram': 6, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidCPUs', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': -1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidRam', response=response)
        response = self.client.post(url, data={'vcpus': 12345, 'ram': 9, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidCPUs', response=response)
        response = self.client.post(url, data={'vcpus': 2, 'ram': 12345, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=400, code='InvalidRam', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)
        # no admin f1 service
        url = reverse('api:admin-flavor-update', kwargs={'id': f1.id})
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        # no admin service2
        self.service.users.add(self.user)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': 'notfound'})
        self.assertErrorResponse(status_code=404, code='ServiceNotExist', response=response)
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': service2.id})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service1, service2 admin ok
        service2.users.add(self.user)
        url = reverse('api:admin-flavor-update', kwargs={'id': f1.id})
        response = self.client.post(url, data={'vcpus': 3, 'ram': 9, 'enable': 'false', 'service_id': service2.id})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'vcpus', 'ram', 'service_id', 'disk', 'flavor_id', 'enable'], response.data)
        self.assertEqual(response.data['vcpus'], 3)
        self.assertEqual(response.data['ram'], 9)
        self.assertEqual(response.data['service_id'], service2.id)
        self.assertEqual(response.data['enable'], False)
        f1.refresh_from_db()
        self.assertEqual(f1.vcpus, 3)
        self.assertEqual(f1.ram, 9)
        self.assertEqual(f1.service_id, service2.id)
        self.assertEqual(f1.enable, False)

        # flavor6 no bind service
        url = reverse('api:admin-flavor-update', kwargs={'id': f6.id})
        response = self.client.post(url, data={'vcpus': 1, 'ram': 1, 'enable': 'true', 'service_id': service2.id})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin ok
        self.service.users.remove(self.user)
        service2.users.remove(self.user)
        self.user.set_federal_admin()
        url = reverse('api:admin-flavor-update', kwargs={'id': f6.id})
        response = self.client.post(url, data={'vcpus': 1, 'ram': 2, 'enable': 'false', 'service_id': service2.id})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'vcpus', 'ram', 'service_id', 'disk', 'flavor_id', 'enable'], response.data)
        self.assertEqual(response.data['vcpus'], 1)
        self.assertEqual(response.data['ram'], 2)
        self.assertEqual(response.data['service_id'], service2.id)
        self.assertEqual(response.data['enable'], False)
        f6.refresh_from_db()
        self.assertEqual(f6.vcpus, 1)
        self.assertEqual(f6.ram, 2)
        self.assertEqual(f6.service_id, service2.id)
        self.assertEqual(f6.enable, False)

        url = reverse('api:admin-flavor-update', kwargs={'id': f6.id})
        response = self.client.post(url, data={'vcpus': 1, 'ram': 2, 'enable': 'true', 'service_id': self.service.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['vcpus'], 1)
        self.assertEqual(response.data['ram'], 2)
        self.assertEqual(response.data['service_id'], self.service.id)
        self.assertEqual(response.data['enable'], True)
        f6.refresh_from_db()
        self.assertEqual(f6.vcpus, 1)
        self.assertEqual(f6.ram, 2)
        self.assertEqual(f6.service_id, self.service.id)
        self.assertEqual(f6.enable, True)
