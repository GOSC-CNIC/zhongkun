from urllib import parse
from decimal import Decimal

from django.urls import reverse

from bill.models import PayApp, PayOrgnazition, PayAppService
from utils.test import get_or_create_user, get_or_create_storage_service
from storage.managers import BucketManager
from storage.models import ObjectsService
from . import MyAPITestCase


class BucketTests(MyAPITestCase):
    def setUp(self):
        self.app = PayApp(
            name='APP name', app_url='', app_desc='test', rsa_public_key='',
            status=PayApp.Status.UNAUDITED.value
        )
        self.app.save(force_insert=True)
        # 余额支付有关配置
        self.po = PayOrgnazition(name='机构')
        self.po.save()
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po
        )
        app_service1.save()
        self.app_service1 = app_service1
        self.service = get_or_create_storage_service()
        self.user = get_or_create_user(username='lilei@xx.com')

    def test_create_bucket(self):
        bucket_name = 'test-bucket'
        url = reverse('api:bucket-list')
        r = self.client.post(url, data={'name': 's', 'service_id': 'ss'})
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.post(url, data={'name': 's', 'service_id': 'ss'})
        self.assertErrorResponse(status_code=400, code='InvalidName', response=r)
        r = self.client.post(url, data={'name': bucket_name, 'service_id': 'ss'})
        self.assertErrorResponse(status_code=404, code='ServiceNotExist', response=r)
        r = self.client.post(url, data={'name': bucket_name, 'service_id': self.service.id})
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=r)

        userpointaccount = self.user.userpointaccount
        userpointaccount.balance = Decimal('200')
        userpointaccount.save(update_fields=['balance'])

        bucket = BucketManager.create_bucket(
            bucket_name=bucket_name, bucket_id='1', user_id=self.user.id, service_id=self.service.id)
        r = self.client.post(url, data={'name': bucket_name, 'service_id': self.service.id})
        self.assertErrorResponse(status_code=409, code='BucketAlreadyExists', response=r)

        r = self.client.post(url, data={'name': 'test_-', 'service_id': self.service.id})
        self.assertErrorResponse(status_code=400, code='InvalidName', response=r)

        r = self.client.post(url, data={'name': 'test_dev', 'service_id': self.service.id})
        self.assertErrorResponse(status_code=500, code='Adapter.BadRequest', response=r)

    def test_delete_bucket(self):
        bucket_name = 'test-bucket'
        url = reverse('api:bucket-delete-bucket', kwargs={'bucket_name': 'test1', 'service_id': 'test'})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': 'test'})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='ServiceNotExist', response=r)

        url = reverse('api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': self.service.id})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        bucket = BucketManager.create_bucket(
            bucket_name=bucket_name, bucket_id='1', user_id=self.user.id, service_id=self.service.id)

        url = reverse('api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': self.service.id})
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 204)

    def test_list_bucket(self):
        user2 = get_or_create_user(username='tom@xx.com')
        self.client.force_login(self.user)
        url = reverse('api:bucket-list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        bucket1 = BucketManager.create_bucket(
            bucket_name='bucket1', bucket_id='1', user_id=self.user.id, service_id=self.service.id)
        bucket2 = BucketManager.create_bucket(
            bucket_name='bucket2', bucket_id='2', user_id=user2.id, service_id=self.service.id)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertKeysIn(keys=[
            'id', 'name', 'creation_time', 'user_id', 'username', 'service'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])

        # query 'service_id'
        url = reverse('api:bucket-list')
        query = parse.urlencode(query={'service_id': 'ss'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'service_id': self.service.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)


class AdminBucketTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@xx.com')
        self.service1 = get_or_create_storage_service()

    def test_list_bucket(self):
        user2 = get_or_create_user(username='tom@xx.com')
        service2 = ObjectsService(
            name='test', name_en='test_en', data_center=self.service1.data_center,
            endpoint_url='',
            username='',
            service_type=ObjectsService.ServiceType.IHARBOR.value,
            api_version=''
        )
        service2.set_password('')
        service2.save(force_insert=True)

        b1_u1_s1 = BucketManager.create_bucket(
            bucket_name='name1', bucket_id='1', user_id=self.user.id, service_id=self.service1.id
        )
        b2_u2_s1 = BucketManager.create_bucket(
            bucket_name='name2', bucket_id='2', user_id=user2.id, service_id=self.service1.id
        )
        b3_u1_s2 = BucketManager.create_bucket(
            bucket_name='name2', bucket_id='2', user_id=self.user.id, service_id=service2.id
        )
        b4_u2_s2 = BucketManager.create_bucket(
            bucket_name='name2', bucket_id='2', user_id=user2.id, service_id=service2.id
        )

        url = reverse('api:admin-bucket-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('api:admin-bucket-list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # service1 admin
        self.service1.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'name', 'creation_time', 'user_id', 'username', 'service',
            'task_status', 'situation', 'situation_time'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)
        self.assertEqual(r.data['results'][1]['id'], b1_u1_s1.id)

        # query 'service_id'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'service_id': service2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)
        self.assertEqual(r.data['results'][1]['id'], b1_u1_s1.id)

        # query 'service_id', 'user_id'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'service_id': self.service1.id, 'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)

        # query 'user_id'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)

        # ----- federal_admin -------------
        self.user.set_federal_admin()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn(keys=[
            'id', 'name', 'creation_time', 'user_id', 'username', 'service',
            'task_status', 'situation', 'situation_time'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])

        # query 'page', 'page_size'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b4_u2_s2.id)
        self.assertEqual(r.data['results'][1]['id'], b3_u1_s2.id)

        query = parse.urlencode(query={'page': 2, 'page_size': 3})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b1_u1_s1.id)

        # query 'service_id'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'service_id': service2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b4_u2_s2.id)
        self.assertEqual(r.data['results'][1]['id'], b3_u1_s2.id)

        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)
        self.assertEqual(r.data['results'][1]['id'], b1_u1_s1.id)

        # query 'user_id'
        url = reverse('api:admin-bucket-list')
        query = parse.urlencode(query={'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b4_u2_s2.id)
        self.assertEqual(r.data['results'][1]['id'], b2_u2_s1.id)

        query = parse.urlencode(query={'user_id': self.user.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b3_u1_s2.id)
        self.assertEqual(r.data['results'][1]['id'], b1_u1_s1.id)

        # query 'service_id', 'user_id'
        query = parse.urlencode(query={'service_id': self.service1.id, 'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)

        query = parse.urlencode(query={'service_id': service2.id, 'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b4_u2_s2.id)
