from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.app_wallet.models import PayApp, PayAppService
from utils.test import get_or_create_user, get_or_create_storage_service, get_or_create_organization, MyAPITestCase
from utils.model import OwnerType
from apps.storage.managers import BucketManager
from apps.storage.models import ObjectsService, Bucket
from apps.storage.bucket_handler import BucketHandler
from apps.servers.models import ResourceActionLog


class BucketTests(MyAPITestCase):
    def setUp(self):
        self.app = PayApp(
            name='APP name', app_url='', app_desc='test', rsa_public_key='',
            status=PayApp.Status.UNAUDITED.value
        )
        self.app.save(force_insert=True)
        # 余额支付有关配置
        self.po = get_or_create_organization(name='机构')
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po
        )
        app_service1.save()
        self.app_service1 = app_service1
        self.service = get_or_create_storage_service()
        self.user = get_or_create_user(username='lilei@xx.com')

    def test_create_bucket(self):
        bucket_name = 'test-bucket'
        url = reverse('storage-api:bucket-list')
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
        url = reverse('storage-api:bucket-delete-bucket', kwargs={'bucket_name': 'test1', 'service_id': 'test'})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('storage-api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': 'test'})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='ServiceNotExist', response=r)

        url = reverse('storage-api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': self.service.id})
        r = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        bucket = BucketManager.create_bucket(
            bucket_name=bucket_name, bucket_id='1', user_id=self.user.id, service_id=self.service.id)

        url = reverse('storage-api:bucket-delete-bucket', kwargs={'bucket_name': bucket_name, 'service_id': self.service.id})
        r = self.client.delete(url)
        self.assertEqual(r.status_code, 204)

        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 1)
        log: ResourceActionLog = ResourceActionLog.objects.order_by('-action_time').first()
        self.assertEqual(log.action_flag, ResourceActionLog.ActionFlag.DELETION.value)
        self.assertEqual(log.resource_id, bucket.id)
        self.assertEqual(log.resource_type, ResourceActionLog.ResourceType.BUCHET.value)
        self.assertEqual(log.owner_type, OwnerType.USER.value)

    def test_list_bucket(self):
        user2 = get_or_create_user(username='tom@xx.com')
        self.client.force_login(self.user)
        url = reverse('storage-api:bucket-list')
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
            'id', 'name', 'creation_time', 'user_id', 'username', 'service',
            'storage_size', 'object_count', 'stats_time'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])

        # query 'service_id'
        url = reverse('storage-api:bucket-list')
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
            name='test', name_en='test_en', org_data_center=self.service1.org_data_center,
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

        url = reverse('storage-api:admin-bucket-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('storage-api:admin-bucket-list')
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
            'task_status', 'situation', 'situation_time', 'storage_size', 'object_count', 'stats_time'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=r.data['results'][0]['service'])
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)
        self.assertEqual(r.data['results'][1]['id'], b1_u1_s1.id)

        # query 'service_id'
        url = reverse('storage-api:admin-bucket-list')
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
        url = reverse('storage-api:admin-bucket-list')
        query = parse.urlencode(query={'service_id': self.service1.id, 'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)

        # query 'user_id'
        url = reverse('storage-api:admin-bucket-list')
        query = parse.urlencode(query={'user_id': user2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], b2_u2_s1.id)

        # ----- 数据中心admin -------------
        self.service1.users.remove(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        self.service1.org_data_center.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)

        # query 'service_id'
        url = reverse('storage-api:admin-bucket-list')
        query = parse.urlencode(query={'service_id': service2.id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], b4_u2_s2.id)
        self.assertEqual(r.data['results'][1]['id'], b3_u1_s2.id)

        # ----- federal_admin -------------
        self.service1.org_data_center.users.remove(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

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
        url = reverse('storage-api:admin-bucket-list')
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
        url = reverse('storage-api:admin-bucket-list')
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
        url = reverse('storage-api:admin-bucket-list')
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

    def test_delete_bucket(self):
        bucket = BucketManager.create_bucket(
            bucket_name='test-bucket', bucket_id='1', user_id=self.user.id, service_id=self.service1.id)

        url = reverse('storage-api:admin-bucket-detail', kwargs={'bucket_name': bucket.name})
        query = parse.urlencode(query={'service_id': 'test'})
        r = self.client.delete(f'{url}?{query}')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.delete(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        url = reverse('storage-api:admin-bucket-detail', kwargs={'bucket_name': 'test1'})
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.delete(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        # AccessDenied
        url = reverse('storage-api:admin-bucket-detail', kwargs={'bucket_name': bucket.name})
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.delete(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # set service admin
        self.service1.users.add(self.user)
        r = self.client.delete(f'{url}?{query}')
        self.assertEqual(r.status_code, 204)

        # test data center admin
        self.service1.users.remove(self.user)
        bucket2 = BucketManager.create_bucket(
            bucket_name='test-bucket2', bucket_id='1', user_id=self.user.id, service_id=self.service1.id)
        # AccessDenied
        url = reverse('storage-api:admin-bucket-detail', kwargs={'bucket_name': bucket2.name})
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.delete(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.service1.org_data_center.users.add(self.user)
        r = self.client.delete(f'{url}?{query}')
        self.assertEqual(r.status_code, 204)

    def test_stats_bucket(self):
        bucket = BucketManager.create_bucket(
            bucket_name='test-bucket', bucket_id='1', user_id=self.user.id, service_id=self.service1.id)

        url = reverse('storage-api:admin-bucket-stats-bucket', kwargs={'bucket_name': bucket.name, 'service_id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        # AccessDenied
        url = reverse('storage-api:admin-bucket-stats-bucket', kwargs={
            'bucket_name': bucket.name, 'service_id': self.service1.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # set service admin
        self.service1.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')

        # test data center admin
        self.service1.users.remove(self.user)
        url = reverse('storage-api:admin-bucket-stats-bucket', kwargs={
            'bucket_name': bucket.name, 'service_id': self.service1.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.service1.org_data_center.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')

        # set federal admin
        self.service1.org_data_center.users.remove(self.user)
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')

    def test_lock_bucket(self):
        bucket = BucketManager.create_bucket(
            bucket_name='test-bucket', bucket_id='1', user_id=self.user.id, service_id=self.service1.id)

        url = reverse('storage-api:admin-bucket-lock', kwargs={'bucket_name': 'bucket'})
        query = parse.urlencode(query={'service_id': 'test'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingParam', response=r)

        query = parse.urlencode(query={'service_id': 'test', 'action': 'test'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={
            'service_id': self.service1.id, 'action': BucketHandler.LockActionChoices.ARREARS_LOCK.value})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        url = reverse('storage-api:admin-bucket-lock', kwargs={'bucket_name': bucket.name})
        query = parse.urlencode(query={
            'service_id': 'test', 'action': BucketHandler.LockActionChoices.ARREARS_LOCK.value})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='BucketNotExist', response=r)

        # AccessDenied
        url = reverse('storage-api:admin-bucket-lock', kwargs={'bucket_name': bucket.name})
        query = parse.urlencode(query={
            'service_id': self.service1.id, 'action': BucketHandler.LockActionChoices.ARREARS_LOCK.value})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # set service admin
        self.service1.users.add(self.user)
        r = self.client.post(f'{url}?{query}')
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')

        # data center admin
        self.service1.users.remove(self.user)
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.service1.org_data_center.users.add(self.user)
        r = self.client.post(f'{url}?{query}')
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')

        # set federal admin
        self.service1.org_data_center.users.remove(self.user)
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        r = self.client.post(f'{url}?{query}')
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.data['code'], 'Adapter.BucketNotExist')


class StatsServiceTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_list_bucket(self):
        user1 = get_or_create_user(username='lilei@xx.com')
        user2 = get_or_create_user(username='tom@xx.com')
        service1 = get_or_create_storage_service()
        service2 = ObjectsService(
            name='test', name_en='test_en', org_data_center=service1.org_data_center,
            endpoint_url='',
            username='',
            service_type=ObjectsService.ServiceType.IHARBOR.value,
            api_version=''
        )
        service2.set_password('')
        service2.save(force_insert=True)

        url = reverse('storage-api:stats-service-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(user1)
        url = reverse('storage-api:stats-service-list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['stats']), 0)

        b1_u1_s1 = Bucket(
            name='name1', bucket_id='1', user_id=user1.id, service_id=service1.id,
            task_status=Bucket.TaskStatus.SUCCESS.value, creation_time=dj_timezone.now(),
            storage_size=123, object_count=12
        )
        b1_u1_s1.save(force_insert=True)
        b2_u2_s1 = Bucket(
            name='name2', bucket_id='2', user_id=user2.id, service_id=service1.id,
            task_status=Bucket.TaskStatus.SUCCESS.value, creation_time=dj_timezone.now(),
            storage_size=242242, object_count=242
        )
        b2_u2_s1.save(force_insert=True)
        b3_u1_s2 = Bucket(
            name='name2', bucket_id='2', user_id=user1.id, service_id=service2.id,
            task_status=Bucket.TaskStatus.SUCCESS.value, creation_time=dj_timezone.now(),
            storage_size=3242242, object_count=542
        )
        b3_u1_s2.save(force_insert=True)
        b4_u2_s2 = Bucket(
            name='name4', bucket_id='4', user_id=user2.id, service_id=service2.id,
            task_status=Bucket.TaskStatus.SUCCESS.value, creation_time=dj_timezone.now(),
            storage_size=575743, object_count=323
        )
        b4_u2_s2.save(force_insert=True)
        b5_u2_s2 = Bucket(
            name='name5', bucket_id='5', user_id=user2.id, service_id=service2.id,
            task_status=Bucket.TaskStatus.SUCCESS.value, creation_time=dj_timezone.now(),
            storage_size=5353678, object_count=446
        )
        b5_u2_s2.save(force_insert=True)

        self.client.force_login(user1)
        url = reverse('storage-api:stats-service-list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        service_map = {}
        for s in r.data['stats']:
            service_map[s['service_id']] = s

        self.assertEqual(len(service_map), 2)
        self.assertEqual(service_map[service1.id]['bucket_count'], 2)
        self.assertEqual(service_map[service1.id]['storage_size'], 123 + 242242)
        self.assertEqual(service_map[service2.id]['bucket_count'], 3)
        self.assertEqual(service_map[service2.id]['storage_size'], 3242242 + 575743 + 5353678)
