from urllib import parse

from django.urls import reverse
from utils.test import get_or_create_user

from bill.models import PayApp, PayAppService, PayOrgnazition
from . import MyAPITestCase


class AppServiceTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@cnic.cn')

        # 余额支付有关配置
        app = PayApp(id='app1id', name='app')
        app.save(force_insert=True)
        app2 = PayApp(id='app2id', name='app2')
        app2.save(force_insert=True)
        self.app = app
        self.app2 = app2
        po = PayOrgnazition(name='机构')
        po.save(force_insert=True)
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id='self.service.id',
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service1.save(force_insert=True)
        self.app_service2 = PayAppService(
            name='service2', app=app2, orgnazition=po, category=PayAppService.Category.VMS_OBJECT.value
        )
        self.app_service2.save(force_insert=True)

    def test_admin_list_app_service(self):
        base_url = reverse('api:app-service-admin-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # set federal admin, list all
        self.user.set_federal_admin()
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'resources', 'desc', 'creation_time', 'status',
            'contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'longitude', 'latitude', 'category', 'orgnazition', 'app_id'
        ], container=r.data['results'][0])

        # unset federal admin, list 0
        self.user.unset_federal_admin()
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # set app_service2 user
        self.app_service2.users.add(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'resources', 'desc', 'creation_time', 'status',
            'contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'longitude', 'latitude', 'category', 'orgnazition', 'app_id'
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['id'], self.app_service2.id)

        # set app_service1.service user
        self.app_service1.users.add(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)

        # query "app_id"
        self.app_service1.users.add(self.user)
        query = parse.urlencode(query={'app_id': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'app_id': self.app.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], self.app_service1.id)

        query = parse.urlencode(query={'app_id': self.app2.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], self.app_service2.id)

    def test_list_app_service(self):
        base_url = reverse('api:app-service-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'resources', 'desc', 'creation_time', 'status',
            # 'contact_person', 'contact_email', 'contact_telephone', 'contact_fixed_phone', 'contact_address',
            'longitude', 'latitude', 'category', 'orgnazition', 'app_id'
        ], container=r.data['results'][0])

        # query "app_id"
        self.app_service1.users.add(self.user)
        query = parse.urlencode(query={'app_id': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'app_id': self.app.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], self.app_service1.id)

        query = parse.urlencode(query={'app_id': self.app2.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], self.app_service2.id)


class AppTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')

    def test_rsa_key_generate(self):
        base_url = reverse('api:trade-rsakey-generate')
        r = self.client.post(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.post(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['key_size', 'private_key', 'public_key'], container=r.data)
