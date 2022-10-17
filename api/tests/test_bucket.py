from urllib import parse
from decimal import Decimal

from django.urls import reverse

from bill.models import PayApp, PayOrgnazition, PayAppService
from utils.test import get_or_create_user, get_or_create_storage_service
from storage.managers import BucketManager
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
