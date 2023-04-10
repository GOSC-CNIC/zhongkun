from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_storage_service
from . import MyAPITestCase


class ObjectsServiceTests(MyAPITestCase):
    def setUp(self):
        self.service = get_or_create_storage_service()
        self.user = get_or_create_user(username='lilei@xx.com')

    def test_list_service(self):
        url = reverse('api:storage-service-list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)    # 不需要登录认证
        # self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'service_type', 'endpoint_url', 'add_time', 'status', 'remarks', 'provide_ftp',
            'ftp_domains', 'longitude', 'latitude', 'pay_app_service_id', 'data_center', 'sort_weight'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en', 'sort_weight'], container=r.data['results'][0]['data_center'])
        self.assertIsInstance(r.data['results'][0]['ftp_domains'], list)

        # query 'center_id'
        url = reverse('api:storage-service-list')
        query = parse.urlencode(query={'center_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'center_id': self.service.data_center_id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # query 'status'
        url = reverse('api:storage-service-list')
        query = parse.urlencode(query={'status': 'sdisable'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStatus', response=r)

        query = parse.urlencode(query={'status': 'disable'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'status': 'enable'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
