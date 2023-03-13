from decimal import Decimal
from urllib import parse
from datetime import date, timedelta

from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_storage_service
from storage.models import ObjectsService
from metering.models import MeteringObjectStorage

from storage.models import Bucket, BucketArchive
from django.utils import timezone
from . import MyAPITestCase


class AdminMeteringStorageTests(MyAPITestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='user1')
        self.user2 = get_or_create_user(username='user2')
        self.service1 = get_or_create_storage_service()
        self.service2 = ObjectsService(
            name='test2', data_center_id=self.service1.data_center_id, endpoint_url='test2', username='', password=''
        )
        self.service2.save(force_insert=True)

    def test_aggregate_metering_by_bucket(self):

        bucket1 = Bucket(
            bucket_id='1', name='bucket1', user=self.user1, service_id=self.service1.id, creation_time=timezone.now())
        bucket1.save(force_insert=True)

        bucket2_archive = BucketArchive(
            original_id=BucketArchive().generate_id(), bucket_id='2', name='bucket2', user=self.user1,
            service_id=self.service2.id,
            creation_time=timezone.now(), delete_time=timezone.now()
        )
        bucket2_archive.save(force_insert=True)

        bucket3 = Bucket(
            bucket_id='3', name='bucket3', user=self.user2, service_id=self.service1.id, creation_time=timezone.now())
        bucket3.save(force_insert=True)

        # bucket1, 2023-02-10 - 2023-03-11
        start_date = date(year=2023, month=2, day=9)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringObjectStorage(
                service_id=bucket1.service_id, user_id=bucket1.user_id, username=bucket1.user.username,
                storage_bucket_id=bucket1.id, bucket_name=bucket1.name, date=start_date,
                storage=i, downstream=i+1, replication=0, put_request=0, get_request=i*10,
                original_amount=Decimal.from_float(i+1), trade_amount=Decimal.from_float(i)
            ).save(force_insert=True)

        # bucket2_archive, 2023-02-05 - 2023-03-06
        start_date = date(year=2023, month=2, day=4)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringObjectStorage(
                service_id=bucket2_archive.service_id, user_id=bucket2_archive.user_id,
                username=bucket2_archive.user.username,
                storage_bucket_id=bucket2_archive.original_id, bucket_name=bucket2_archive.name, date=start_date,
                storage=2*i, downstream=2*i+1, replication=0, put_request=0, get_request=i*20,
                original_amount=Decimal.from_float(i+6), trade_amount=Decimal.from_float(i+1)
            ).save(force_insert=True)

        # bucket3, 2023-01-20 - 2023-02-18
        start_date = date(year=2023, month=1, day=19)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringObjectStorage(
                service_id=bucket3.service_id, user_id=bucket3.user_id,
                username=bucket3.user.username,
                storage_bucket_id=bucket3.id, bucket_name=bucket3.name, date=start_date,
                storage=3*i, downstream=3*i + 1, replication=0, put_request=0, get_request=i * 30,
                original_amount=Decimal.from_float(3*i+6), trade_amount=Decimal.from_float(3*i+1)
            ).save(force_insert=True)

        base_url = reverse('api:admin-metering-storage-aggregation-by-bucket')

        # NotAuthenticated
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user1)

        # invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-31'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_end
        query = parse.urlencode(query={
            'date_end': '2022-2-1'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # AccessDenied, user1 no permission of service1
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # list user aggregate metering, default current month
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 
        
        # list user aggregate metering, date_start - date_end, no service that has permission
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

        # list user aggregate metering, service1(bucket1/3), date_start - date_end
        self.service1.users.add(self.user1)
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn([
            'count', 'page_num', 'page_size', 'results'
        ], r.data)
        self.assertKeysIn([
            'storage_bucket_id', 'total_storage_hours', 'total_downstream', 'total_get_request',
            'total_original_amount', 'total_trade_amount', 'service', 'user', 'bucket'
        ], r.data['results'][0])
        self.assertKeysIn(['id', 'name'], r.data['results'][0]['service'])
        self.assertKeysIn(['id', 'username'], r.data['results'][0]['user'])
        self.assertKeysIn(['id', 'name'], r.data['results'][0]['bucket'])

        # --------- 2023-02-01 - 2023-02-28 ----------
        # service1(bucket1/3), date_start - date_end, order_by
        self.service1.users.add(self.user1)

        # bucket1 2023-02-10 - 02-28, 19 days
        total_storage1 = 0      # 171
        total_downstream1 = 0   # 190
        total_get_request1 = 0  # 1710
        total_original_amount1 = Decimal('0')   # 190
        total_trade_amount1 = Decimal('0')      # 171
        for i in range(19):
            total_storage1 += i
            total_downstream1 += i + 1
            total_get_request1 += 10 * i
            total_original_amount1 += Decimal.from_float(i + 1)
            total_trade_amount1 += Decimal.from_float(i)

        # bucket3 2023-02-01 - 02-18, 18 days
        total_storage3 = 0      # 1107
        total_downstream3 = 0   # 1125
        total_get_request3 = 0  # 11070
        total_original_amount3 = Decimal('0')   # 1215
        total_trade_amount3 = Decimal('0')      # 1125
        for i in range(30 - 18, 30):
            total_storage3 += 3 * i
            total_downstream3 += 3 * i + 1
            total_get_request3 += i * 30
            total_original_amount3 += Decimal.from_float(3 * i + 6)
            total_trade_amount3 += Decimal.from_float(3 * i + 1)

        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
            'order_by': 'total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        bm1 = r.data['results'][0]
        bm3 = r.data['results'][1]
        self.assertEqual(bm1['storage_bucket_id'], bucket1.id)
        self.assertEqual(bm1['total_storage_hours'], total_storage1)
        self.assertEqual(bm1['total_downstream'], total_downstream1)
        self.assertEqual(bm1['total_get_request'], total_get_request1)
        self.assertEqual(Decimal(bm1['total_original_amount']), total_original_amount1)
        self.assertEqual(Decimal(bm1['total_trade_amount']), total_trade_amount1)
        self.assertEqual(bm1['user']['id'], bucket1.user_id)
        self.assertEqual(bm1['user']['username'], bucket1.user.username)
        self.assertEqual(bm1['service']['id'], bucket1.service_id)

        self.assertEqual(bm3['storage_bucket_id'], bucket3.id)
        self.assertEqual(bm3['user']['id'], bucket3.user_id)
        self.assertEqual(bm3['user']['username'], bucket3.user.username)
        self.assertEqual(bm3['service']['id'], bucket3.service_id)
        self.assertEqual(bm3['total_storage_hours'], total_storage3)
        self.assertEqual(bm3['total_downstream'], total_downstream3)
        self.assertEqual(bm3['total_get_request'], total_get_request3)
        self.assertEqual(Decimal(bm3['total_original_amount']), total_original_amount3)
        self.assertEqual(Decimal(bm3['total_trade_amount']), total_trade_amount3)

        # service1(bucket1/3), date_start - date_end, order_by
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket3.id)
        self.assertEqual(r.data['results'][1]['storage_bucket_id'], bucket1.id)

        # service1(bucket1/3), date_start - date_end, order_by, page_size
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
            'order_by': '-total_original_amount', 'page_size': 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket3.id)

        # service1(bucket1/3), date_start - date_end, order_by
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
            'order_by': 'total_storage_hours'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket1.id)
        self.assertEqual(r.data['results'][1]['storage_bucket_id'], bucket3.id)

        # federal admin
        self.user1.set_federal_admin()

        # bucket3 2023-02-05 - 02-28, 24 days
        total_storage2 = 0  # 744
        total_downstream2 = 0  # 768
        total_get_request2 = 0  # 7440
        total_original_amount2 = Decimal('0')  # 516
        total_trade_amount2 = Decimal('0')  # 396
        for i in range(4, 28):
            total_storage2 += 2 * i
            total_downstream2 += 2 * i + 1
            total_get_request2 += i * 20
            total_original_amount2 += Decimal.from_float(i + 6)
            total_trade_amount2 += Decimal.from_float(i + 1)

        # date_start - date_end, order_by
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
            'order_by': 'total_storage_hours'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket1.id)
        self.assertEqual(r.data['results'][1]['storage_bucket_id'], bucket2_archive.original_id)
        self.assertEqual(r.data['results'][2]['storage_bucket_id'], bucket3.id)

        # 归档桶信息验证
        bm2 = r.data['results'][1]
        self.assertEqual(bm2['bucket']['id'], bucket2_archive.original_id)
        self.assertEqual(bm2['bucket']['name'], bucket2_archive.name)
        self.assertEqual(bm2['user']['id'], bucket2_archive.user_id)
        self.assertEqual(bm2['user']['username'], bucket2_archive.user.username)
        self.assertEqual(bm2['service']['id'], bucket2_archive.service_id)
        self.assertEqual(bm2['service']['name'], bucket2_archive.service.name)

        # -----  federal admin  -----------
        # date_start - date_end, only bucket1/2
        query = parse.urlencode(query={
            'date_start': '2023-03-01', 'date_end': '2023-03-28'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket1.id)
        self.assertEqual(r.data['results'][1]['storage_bucket_id'], bucket2_archive.original_id)

        # date_start - date_end, only bucket1
        query = parse.urlencode(query={
            'date_start': '2023-03-08', 'date_end': '2023-03-28'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket1.id)

        # date_start - date_end, only bucket3
        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-02'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['storage_bucket_id'], bucket3.id)
