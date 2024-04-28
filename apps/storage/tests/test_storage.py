from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from apps.storage.models import Bucket, ObjectsService
from utils.test import get_or_create_user, get_or_create_storage_service, MyAPITestCase


class ObjectsServiceTests(MyAPITestCase):
    def setUp(self):
        self.service = get_or_create_storage_service()
        self.user = get_or_create_user(username='lilei@xx.com')

    def test_list_service(self):
        url = reverse('storage-api:storage-service-list')
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
            'ftp_domains', 'longitude', 'latitude', 'pay_app_service_id', 'org_data_center', 'sort_weight', 'version'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'sort_weight', 'organization'], container=r.data['results'][0]['org_data_center'])
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en'], container=r.data['results'][0]['org_data_center']['organization'])
        self.assertIsInstance(r.data['results'][0]['ftp_domains'], list)

        # query 'org_id'
        url = reverse('storage-api:storage-service-list')
        query = parse.urlencode(query={'org_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'org_id': self.service.org_data_center.organization_id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # query 'center_id'
        url = reverse('storage-api:storage-service-list')
        query = parse.urlencode(query={'center_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'center_id': self.service.org_data_center_id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # query 'status'
        url = reverse('storage-api:storage-service-list')
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

    def test_admin_list_service(self):
        service2 = ObjectsService(name='test2', name_en='en2', org_data_center=None)
        service2.save(force_insert=True)

        url = reverse('storage-api:storage-service-admin-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # set admin
        self.service.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'service_type', 'endpoint_url', 'add_time', 'status', 'remarks', 'provide_ftp',
            'ftp_domains', 'longitude', 'latitude', 'pay_app_service_id', 'org_data_center', 'sort_weight', 'version'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'sort_weight', 'organization'], container=r.data['results'][0]['org_data_center'])
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en'], container=r.data['results'][0]['org_data_center']['organization'])
        self.assertIsInstance(r.data['results'][0]['ftp_domains'], list)

        # query 'org_id'
        url = reverse('storage-api:storage-service-admin-list')
        query = parse.urlencode(query={'org_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'org_id': self.service.org_data_center.organization_id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # query 'center_id'
        url = reverse('storage-api:storage-service-admin-list')
        query = parse.urlencode(query={'center_id': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        query = parse.urlencode(query={'center_id': self.service.org_data_center_id})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # query 'status'
        url = reverse('storage-api:storage-service-admin-list')
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

        # 数据中心管理员
        self.service.users.remove(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        self.service.org_data_center.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # 同时为数据中心和服务单元管理员
        self.service.users.add(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)

        # 联邦管理员
        self.service.users.remove(self.user)
        self.service.org_data_center.users.remove(self.user)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # set admin
        self.user.set_federal_admin()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'next', 'previous', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'service_type', 'endpoint_url', 'add_time', 'status', 'remarks', 'provide_ftp',
            'ftp_domains', 'longitude', 'latitude', 'pay_app_service_id', 'org_data_center', 'sort_weight', 'version'
        ], container=r.data['results'][0])
        self.assertKeysIn(keys=[
            'id', 'name', 'name_en', 'sort_weight', 'organization'], container=r.data['results'][0]['org_data_center'])
        self.assertIsInstance(r.data['results'][0]['ftp_domains'], list)


class StorageStatisticsTests(MyAPITestCase):
    def setUp(self):
        self.service = get_or_create_storage_service()
        self.user = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='张三@xx.com')

    def test_storage_statistics(self):
        url = reverse('storage-api:admin-storage-statistics-list')
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'current_bucket_count', 'new_bucket_count', 'new_bucket_delete_count',
            'total_storage_size', 'total_object_count'
        ], container=r.data)
        self.assertEqual(r.data['current_bucket_count'], 0)
        self.assertEqual(r.data['serving_user_count'], 0)
        self.assertEqual(r.data['new_bucket_count'], 0)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 0)
        self.assertEqual(r.data['total_object_count'], 0)

        nt = timezone.now()
        # query "time_end" < "time_start"
        query = parse.urlencode(query={
            'time_start': '2023-04-24T08:08:25Z', 'time_end': '2023-04-24T08:08:24Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        # invalid "time_start"
        query = parse.urlencode(query={
            'time_start': '2023-04-24T08:082Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={
            'time_start': '2023-03-24T00:00:00Z', 'time_end': '2023-04-24T00:00:00Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 0)
        self.assertEqual(r.data['serving_user_count'], 0)
        self.assertEqual(r.data['new_bucket_count'], 0)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 0)
        self.assertEqual(r.data['total_object_count'], 0)

        # init data
        bucket1 = Bucket(
            name='bucket-name1', bucket_id='1', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=111, object_count=1,
            user_id=self.user.id, service_id=None, creation_time=nt
        )
        bucket1.save(force_insert=True)

        bucket2 = Bucket(
            name='bucket-name2', bucket_id='2', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=222, object_count=2,
            user_id=self.user.id, service_id=self.service.id, creation_time=nt - timedelta(days=1)
        )
        bucket2.save(force_insert=True)

        bucket3 = Bucket(
            name='bucket-name3', bucket_id='3', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=333, object_count=3,
            user_id=self.user.id, service_id=self.service.id, creation_time=nt - timedelta(days=6)
        )
        bucket3.save(force_insert=True)

        bucket4 = Bucket(
            name='bucket-name4', bucket_id='4', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=444, object_count=4,
            user_id=self.user2.id, service_id=None, creation_time=nt - timedelta(days=8)
        )
        bucket4.save(force_insert=True)

        bucket5 = Bucket(
            name='bucket-name5', bucket_id='5', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=555, object_count=5,
            user_id=self.user.id, service_id=None, creation_time=nt - timedelta(days=30)
        )
        bucket5.save(force_insert=True)

        bucket6 = Bucket(
            name='bucket-name6', bucket_id='6', task_status=Bucket.TaskStatus.SUCCESS.value,
            storage_size=666, object_count=6,
            user_id=None, service_id=self.service.id, creation_time=nt - timedelta(days=60)
        )
        bucket6.save(force_insert=True)

        # all
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 6)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 6)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 111 + 222 + 333 + 444 + 555 + 666)
        self.assertEqual(r.data['total_object_count'], 1 + 2 + 3 + 4 + 5 + 6)

        # query "service_id"
        query = parse.urlencode(query={
            'service_id': 'test'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 0)
        self.assertEqual(r.data['serving_user_count'], 0)
        self.assertEqual(r.data['new_bucket_count'], 0)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 0)
        self.assertEqual(r.data['total_object_count'], 0)

        query = parse.urlencode(query={
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 3)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 3)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 222 + 333 + 666)
        self.assertEqual(r.data['total_object_count'], 2 + 3 + 6)

        # query "time_start" "time_end"
        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 6)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 4)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 111 + 222 + 333 + 444)
        self.assertEqual(r.data['total_object_count'], 1 + 2 + 3 + 4)

        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'time_end': (nt - timedelta(days=2)).isoformat()[0:19] + 'Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 6)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 2)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 333 + 444)
        self.assertEqual(r.data['total_object_count'], 3 + 4)

        # query "time_start"、 "time_end" 、 "service_id"
        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 3)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 2)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 222 + 333)
        self.assertEqual(r.data['total_object_count'], 2 + 3)

        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'time_end': (nt - timedelta(days=2)).isoformat()[0:19] + 'Z',
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 3)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 1)
        self.assertEqual(r.data['new_bucket_delete_count'], 0)
        self.assertEqual(r.data['total_storage_size'], 333)
        self.assertEqual(r.data['total_object_count'], 3)

        bucket3.do_archive(archiver='test')
        bucket5.do_archive(archiver='test')

        # all
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 4)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 4)
        self.assertEqual(r.data['new_bucket_delete_count'], 2)
        self.assertEqual(r.data['total_storage_size'], 111 + 222 + 444 + 666)
        self.assertEqual(r.data['total_object_count'], 1 + 2 + 4 + 6)

        # query "service_id"
        query = parse.urlencode(query={
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 2)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 2)
        self.assertEqual(r.data['new_bucket_delete_count'], 1)
        self.assertEqual(r.data['total_storage_size'], 222 + 666)
        self.assertEqual(r.data['total_object_count'], 2 + 6)

        # query "time_start" "time_end"
        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 4)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 3)  # bucket 1 2 4
        self.assertEqual(r.data['new_bucket_delete_count'], 1)  # bucket 3
        self.assertEqual(r.data['total_storage_size'], 111 + 222 + 444)
        self.assertEqual(r.data['total_object_count'], 1 + 2 + 4)

        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'time_end': (nt - timedelta(days=2)).isoformat()[0:19] + 'Z'
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 4)
        self.assertEqual(r.data['serving_user_count'], 2)
        self.assertEqual(r.data['new_bucket_count'], 1)  # bucket 4
        self.assertEqual(r.data['new_bucket_delete_count'], 1)  # bucket 3
        self.assertEqual(r.data['total_storage_size'], 444)
        self.assertEqual(r.data['total_object_count'], 4)

        # query "time_start" "time_end" "service_id"
        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 2)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 1)  # bucket 2
        self.assertEqual(r.data['new_bucket_delete_count'], 1)  # bucket 3
        self.assertEqual(r.data['total_storage_size'], 222)
        self.assertEqual(r.data['total_object_count'], 2)

        query = parse.urlencode(query={
            'time_start': (nt - timedelta(days=10)).isoformat()[0:19] + 'Z',
            'time_end': (nt - timedelta(days=2)).isoformat()[0:19] + 'Z',
            'service_id': self.service.id
        })
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['current_bucket_count'], 2)
        self.assertEqual(r.data['serving_user_count'], 1)
        self.assertEqual(r.data['new_bucket_count'], 0)
        self.assertEqual(r.data['new_bucket_delete_count'], 1)  # bucket 3
        self.assertEqual(r.data['total_storage_size'], 0)
        self.assertEqual(r.data['total_object_count'], 0)
